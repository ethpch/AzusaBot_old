import logging
import aiofiles
import os
import re
import io
import random
from copy import deepcopy
from collections import Counter
from typing import Generator
from pixivpy_async import AppPixivAPI, PixivError
from PIL import Image
from Azusa.log import debuglog
from Azusa.utils import storage, convert_to_b64
from Azusa.exceptions import InfoNotFoundError

logger = logging.getLogger('Azusa.pixiv')

try:
    debuglog
except NameError:
    def debuglog(*_, **__):
        def deco(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return deco

class pixiv_image():
    """ 对pixivpy_async的封装。
    单独使用请注释掉“Azusa”相关的内容，包括import语句，debuglog，storage，convert_to_b64，并且重写一个InfoNotFoundError。
        ```
        class InfoNotFouneError(PixivError):
            pass
        ```
    """
    @debuglog(logger)
    def __init__(self, username: str, password: str, proxy_url: str='', imagepath: str=''):
        if imagepath:
            self.__imagepath = imagepath
            self.__pathflag = True
        else:
            self.__imagepath = os.path.join(os.path.dirname(__file__), 'image')
            self.__pathflag = False
        if not os.path.exists(self.__imagepath):
            try:
                os.mkdir(self.__imagepath)
            except FileNotFoundError as e:
                logger.exception('directory error')
                raise e
        self.__api = EnhancedAPI()
        self.__api.set_accept_language('zh-cn')
        if proxy_url:
            self.__api.set_api_proxy(app_hosts = proxy_url, auth_hosts = proxy_url, pub_hosts = proxy_url)
        self.__username = username
        self.__password = password
        self.__pagesize = 30
        self.__loginflag = False
        self.__data = {'illusts': {}, 'users': {}}
        self.__storage = storage.getStorageObj('pixiv')
        self.pload()

    # 登录
    @debuglog(logger)
    async def login(self):
        if self.__username and self.__password:
            try:
                await self.__api.login(self.__username, self.__password)
                self.__loginflag = True
            except PixivError:
                self.__loginflag = False
        else:
            self.__loginflag = False

    # 设置多图片查找，单页结果数据量
    @debuglog(logger)
    def set_pagesize(self, pagesize: int):
        self.__pagesize = pagesize

    # 保存图库信息
    @debuglog(logger)
    def psave(self):
        self.__storage.save('data', self.__data)

    # 写入图库信息
    @debuglog(logger)
    def pload(self):
        d = self.__storage.load('data')
        try:
            for k, v in d.items():
                self.__data[k] = {int(k1): v1 for k1, v1 in v.items()}
            for k in self.__data['illusts'].keys():
                for k1 in self.__data['illusts'][k]['files'].keys():
                    for item in self.__data['illusts'][k]['files'][k1]:
                        if not os.path.exists(os.path.join(self.__imagepath, item.split(os.sep)[-1])):
                            self.__data['illusts'][k]['files'][k1].remove(item)
        except KeyError:
            pass

    # 写入图片信息
    @debuglog(logger)
    async def __newpic(self, illust: dict):
        id = illust.id
        d = {
            'tags': tuple(illust.tags),
            'views': illust.total_view,
            'bookmarks': illust.total_bookmarks,
            'comments': illust.total_comments if 'total_comments' in illust.keys() else 0,
            }
        if id not in self.__data['illusts'].keys():
            self.__data['illusts'][id] = {
                'title': illust.title,
                'caption': illust.caption,
                'id': illust.id,
                'type': '插画' if illust.type == 'illust' else '漫画',
                'count': illust.page_count,
                'time': illust.create_date.split('T')[0] + ' ' + illust.create_date.split('T')[1].split('+')[0],
                'author_name': illust.user.name,
                'author_id': illust.user.id,
                'urls': {},
                'files': {
                    'original': [],
                    'large': [],
                    },
                }
            if illust.meta_pages:
                self.__data['illusts'][id]['urls']['large'] = [item.image_urls.large for item in illust.meta_pages]
                self.__data['illusts'][id]['urls']['original'] = [item.image_urls.original for item in illust.meta_pages]
            else:
                self.__data['illusts'][id]['urls']['large'] = [illust.image_urls.large]
                self.__data['illusts'][id]['urls']['original'] = [illust.meta_single_page.original_image_url]
        self.__data['illusts'][id].update(d)
        if self.__data['illusts'][id]['author_id'] not in self.__data['users'].keys():
            self.__data['users'][self.__data['illusts'][id]['author_id']] = {
                'user': {
                    'id': self.__data['illusts'][id]['author_id'],
                    'name': self.__data['illusts'][id]['author_name'],
                    },
                'profile': {},
                'workspace': {},
                'illusts': [id]
                }
        if id not in self.__data['users'][self.__data['illusts'][id]['author_id']]['illusts']:
            self.__data['users'][self.__data['illusts'][id]['author_id']]['illusts'].append(id)

    # 写入作者信息
    @debuglog(logger)
    async def __newuser(self, user: dict, profile: dict={}, workspace: dict={}, illusts: list=[]):
        id = user.id
        if id not in self.__data['users'].keys():
            self.__data['users'][id] = {'user': {}}
        self.__data['users'][id]['user'].update(user)
        if profile or 'profile' not in self.__data['users'][id].keys():
            self.__data['users'][id]['profile'] = profile
        if workspace or 'workspace' not in self.__data['users'][id].keys():
            self.__data['users'][id]['workspace'] = workspace
        if 'illusts' not in self.__data['users'][id].keys():
            self.__data['users'][id]['illusts'] = []
        if illusts:
            for illust in illusts:
                id = illust.id
                if id not in self.__data['users'][id]['illusts']:
                    self.__data['users'][id]['illusts'].append(id)

    # 获取图片信息
    @debuglog(logger)
    def getpics(self, pids: tuple, useb64: bool=False) -> Generator:
        """
        获取图片。
        参数：
            pids：需要获取的图片pid组成的元组
        返回值：
            返回生成器，由图片字典元素组成，字段说明如下：
                title：作品标题
                caption: 作品说明
                id：作品ID
                type：作品类型
                count：作品页数
                time：作品上传时间
                tags：[{
                    name：作品标签
                    translated_name：翻译标签
                    }]
                author_name：作者名
                author_id：作者ID
                views：阅读数
                bookmarks：收藏数
                comments：评论数
                files：{
                    original: 原图
                    large: 小图
                    }
        异常：
            KeyError：图库图片中不包含所有输入的pid
        """
        if not self.__pathflag:
            useb64 = True
        for pid in pids:
            if useb64:
                res = deepcopy(self.__data['illusts'][pid])
                for k in res['files'].keys():
                    for i in range(len(res['files'][k])):
                        realpath = os.path.join(self.__imagepath, os.pardir, res['files'][k][i]) \
                            if self.__pathflag else res['files'][k][i]
                        res['files'][k][i] = convert_to_b64(realpath)
                yield res
            else:
               yield self.__data['illusts'][pid].copy()

    # 获取用户信息
    @debuglog(logger)
    def getusers(self, uids: tuple, useb64: bool=False) -> Generator:
        """
        获取用户。
        参数：
            uids：需要获取的用户uid组成的元组
        返回值：
            返回一个生成器，由用户字典元素组成，字段说明如下：
                {
                    'user': {
                        'id': 用户id,
                        'name': 用户昵称,
                        'account': 用户帐号,
                        'profile_image': 用户头像,
                        'comment': 用户自我介绍,
                        },
                    'profile': {
                        'webpage': 用户网站,
                        'gender': 用户性别,
                        'region': 国家或地区,
                        'job': 职业,
                        'total_follow_users': 关注人数,
                        'total_mypixiv_users': 好P友人数,
                        'total_illusts': 插画数,
                        'total_manga': 漫画数,
                        'total_novels': 小说数,
                        'total_illust_bookmarks_public': 公开收藏作品数,
                        'total_illust_series': 系列插画数,
                        'total_novel_series': 系列小说数,
                        'background_image': 个人资料背景图,
                        'twitter_account': twitter帐号,
                        'twitter_url': twitter链接地址,
                        'pawoo_url': pawoo链接地址,
                        },
                    'workspace': {
                        'pc': 电脑,
                        'monitor': 显示器,
                        'tool': 软件,
                        'scanner': 扫描仪,
                        'tablet': 数位板,
                        'mouse': 鼠标,
                        'printer': 打印机,
                        'desktop': 桌子上的东西,
                        'music': 绘图时听的音乐,
                        'desk': 桌子,
                        'chair': 椅子,
                        'comment': 其他,
                        'workspace_image': 工作环境图,
                        }
                }
        异常：
            KeyError：图库作者中不包含所有输入的uid
        """
        if not self.__pathflag:
            useb64 = True
        for uid in uids:
            if useb64:
                res = deepcopy(self.__data['users'][uid])
                res['user']['profile_image'] = convert_to_b64(os.path.join(self.__imagepath, os.pardir, \
                    res['user']['profile_image']) if self.__pathflag else res['user']['profile_image'])
                res['profile']['background_image'] = convert_to_b64(os.path.join(self.__imagepath, os.pardir, \
                    res['profile']['background_image']) if self.__pathflag else res['profile']['background_image'])
                res['workspace']['workspace_image'] = convert_to_b64(os.path.join(self.__imagepath, os.pardir, \
                    res['workspace']['workspace_image']) if self.__pathflag else res['workspace']['workspace_image'])
                yield res
            else:
                yield self.__data['users'][uid].copy()

    # 查询作品详细信息
    @debuglog(logger)
    async def illust_detail(self,
            pid: int,
            *,
            original_image: bool=False,
            multiimage: bool=False,
            allowr18: bool=False,
            allowr18g: bool=False
        ) -> tuple:
        """
        查询作品详细信息。
        参数：
            pid：作品PID
            original_image：是否使用原图
            multiimage：多图作品是否使用多图
            allowr18：是否允许R18
            allowr18g：是否允许R18G
        返回值：
            返回一个元组，由pid组成
        """
        if pid not in self.__data['illusts'].keys():
            json_result = await self.__api.illust_detail(pid, req_auth=self.__loginflag)
            if 'error' in json_result.keys():
                raise InfoNotFoundError
            illust = json_result.illust
            await self.__newpic(illust)
        if allowr18g:
            flag = True
        else:
            if 'R-18' in str(self.__data['illusts'][pid]['tags']) or 'R18' in str(self.__data['illusts'][pid]['tags']):
                flag = False
            else:
                if allowr18:
                    flag = True
                else:
                    if 'R-18G' in str(self.__data['illusts'][pid]['tags']) or 'R18G' in str(self.__data['illusts'][pid]['tags']):
                        flag = False
                    else:
                        flag = True
        if flag:
            await self.__download(pid, original_image, multiimage)
        return (pid,)

    # 查询作品评论
    @debuglog(logger)
    async def illust_comments(self, pid: int) -> tuple:
        """
        查询作品评论。
        参数：
            pid：作品PID
        返回值：
            评论元组，由多条评论组成
        """
        json_result = await self.__api.illust_comments(pid, req_auth=self.__loginflag)
        if 'error' in json_result.keys():
            raise InfoNotFoundError
        comments = json_result.comments
        res = []
        for comment in comments:
            user = comment.user.name
            time = comment.date.split('T')[0] + ' ' + comment.date.split('T')[1].split('+')[0]
            content = comment.comment
            res.append(
                '-' * 10 + '\n' +
                f'{user} 发送于 {time}（JTC）{"给 " + comment.parent_comment.user.name if comment.parent_comment else ""}：\n{content}\n'
                )
        return tuple(res)

    #@debuglog(logger)
    #async def ugoira_metadata(self, pid: int) -> tuple:
    #    json_result = await self.__api.ugoira_metadata(pid, req_auth=self.__loginflag)
    #    metadata = json_result.ugoira_metadata
    #    return tuple(len(metadata.frames), metadata.zip_urls.medium)

    # 查询排行榜
    @debuglog(logger)
    async def illust_ranking(self, mode: str, date: str=None, *args, **kwargs) -> tuple:
        '''
        查询P站排行榜。
        参数：
            mode：可选值为：
                    day | week | month | day_male | day_female | week_original | week_rookie | 
                    day_r18 | day_male_r18 | day_female_r18 | week_r18 | week_r18g | 
                    day_manga | week_manga | month_manga | week_rookie_manga | 
                    day_r18_manga | week_r18_manga | week_r18g_manga 
            date：查询日期
            
            page：页数
            min_bookmarks：选择图片的最低收藏数
            original_image：是否使用原图
            multiimage：多图作品是否使用多图
            allowr18：是否允许R18
            allowr18g：是否允许R18G
        返回值：
            返回一个元组，由pid组成
        '''
        json_result = await self.__api.illust_ranking(mode=mode, date=date, req_auth=self.__loginflag)
        func = self.__api.illust_ranking
        return await self.__illustcontent(json_result, func, *args, **kwargs)

    # 查询推荐作品
    @debuglog(logger)
    async def illust_recommended(self, *args, type='illust', **kwargs) -> tuple:
        """
        查询推荐作品。
        参数：
            type: 作品类型（'illust' or 'manga'）

            page：页数
            min_bookmarks：选择图片的最低收藏数
            original_image：是否使用原图
            multiimage：多图作品是否使用多图
            allowr18：是否允许R18
            allowr18g：是否允许R18G
        返回值：
            返回一个元组，由pid组成
        """
        json_result = await self.__api.illust_recommended(content_type=type, req_auth=self.__loginflag)
        func = self.__api.illust_recommended
        return await self.__illustcontent(json_result, func, *args, **kwargs)

    # 查询相似作品
    @debuglog(logger)
    async def illust_related(self, pid: int, *args, **kwargs) -> tuple:
        """
        查询相似作品。
        参数：
            pid：作品PID

            type：作品类型（'illust' or 'manga'）
            page：页数
            min_bookmarks：选择图片的最低收藏数
            original_image：是否使用原图
            multiimage：多图作品是否使用多图
            allowr18：是否允许R18
            allowr18g：是否允许R18G
        返回值：
            返回一个元组，由pid组成
        """
        json_result = await self.__api.illust_related(pid, req_auth=self.__loginflag)
        func = self.__api.illust_related
        return await self.__illustcontent(json_result, func, *args, **kwargs)

    # 搜索功能
    @debuglog(logger)
    async def search_illust(self, keywords: str, *args, search_target: str='partial_match_for_tags', min_bookmarks: int=0, **kwargs) -> tuple:
        """
        搜索图片功能。
        参数：
            keywords：关键字字符串
            search_target：可选值为：
                    partial_match_for_tags | exact_match_for_tags | title_and_caption
            min_bookmarks：选择图片的最低收藏数

            type：作品类型（'illust' or 'manga'）
            page：页数
            original_image：是否使用原图
            multiimage：多图作品是否使用多图
            allowr18：是否允许R18
            allowr18g：是否允许R18G
        返回值：
            返回一个元组，由pid组成
        """
        keywords_list = keywords.split(' ')
        result_keywords_list = []
        for item in keywords_list:
            class jumpout(Exception):
                pass
            try:
                local_targeted_tags = []
                for id in self.__data['illusts'].keys():
                    for tag in self.__data['illusts'][id]['tags']:
                        if item == tag['name'] or item == tag['translated_name']:
                            result_keywords_list.append(tag['name'])
                            raise jumpout
                        elif tag['translated_name'] and item in tag['translated_name'] and not tag['name'].endswith('users入り'):
                            local_targeted_tags.append(tag['name'])
                local_targeted_tags_counter = Counter(local_targeted_tags)
                result_keywords_list.append(local_targeted_tags_counter.most_common(1)[0][0] if local_targeted_tags_counter else item)
            except jumpout:
                pass
        if result_keywords_list:
            keywords = ' '.join(result_keywords_list)
        if min_bookmarks >= 5000:
            keywords += ' users入り'
        json_result = await self.__api.search_illust(word=keywords, search_target=search_target, req_auth=self.__loginflag)
        func = self.__api.search_illust
        kwargs['min_bookmarks'] = min_bookmarks
        return await self.__illustcontent(json_result, func, *args, **kwargs)

    # 查询用户详细信息
    @debuglog(logger)
    async def user_detail(self, uid: int) -> tuple:
        """
        依据UID搜索用户详细信息。
        参数：
            uid：P站UID
        返回值：
            返回一个元组，由uid组成
        """
        json_result = await self.__api.user_detail(uid)
        user = json_result.user
        profile = json_result.profile
        workspace = json_result.workspace
        await self.__newuser(user, profile, workspace)
        await self.__udownload(uid)
        return (uid,)

    # 搜索用户
    @debuglog(logger)
    async def search_user(self, keywords: str, *args, **kwargs) -> tuple:
        """
        搜索用户功能。
        参数：
            keywords：关键字字符串
        返回值：
            返回一个元组，由uid组成
        """
        json_result = await self.__api.search_user(word=keywords)
        func = self.__api.search_user
        return await self.__usercontent(json_result, func, *args, **kwargs)

    # 用户作品列表
    @debuglog(logger)
    async def user_illusts(self, uid: int, type='illust', *args, **kwargs) -> tuple:
        """
        依据UID搜索用户所有作品。
        参数：
            uid：P站UID
            type：作品类型（'illust' or 'manga'）

            page: 页数
            min_bookmarks：选择图片的最低收藏数
            original_image：是否使用原图
            multiimage：多图作品是否使用多图
            allowr18：是否允许R18
            allowr18g：是否允许R18G
        返回值：
            返回一个元组，由pid组成
        """
        json_result = await self.__api.user_illusts(uid, type=type)
        func = self.__api.user_illusts
        return await self.__illustcontent(json_result, func, *args, **kwargs)

    # 关注用户
    @debuglog(logger)
    async def user_following(self, uid: int, *args, **kwargs):
        """
        查询指定用户的关注用户列表。
        参数：
            uid: 指定用户的uid
            page: 页数设置
        返回值：
            返回一个元组，由uid组成
        """
        json_result = await self.__api.user_following(uid)
        func = self.__api.user_following
        return await self.__usercontent(json_result, func, *args, **kwargs)

    # 好P友
    @debuglog(logger)
    async def user_mypixiv(self, uid: int, *args, **kwargs):
        """
        查询指定用户的好P友。
        参数：
            uid: 指定用户的uid
            page: 页数设置
        返回值：
            返回一个元组，由uid组成
        """
        json_result = await self.__api.user_mypixiv(uid)
        func = self.__api.user_mypixiv
        return await self.__usercontent(json_result, func, *args, **kwargs)
    
    # 用户收藏作品列表
    @debuglog(logger)
    async def user_bookmarks_illust(self, uid: int, *args, **kwargs) -> tuple:
        """
        依据UID搜索用户所有插画列表。
        参数：
            uid：P站UID

            type：作品类型（'illust' or 'manga'）
            page：页数
            min_bookmarks：选择图片的最低收藏数
            original_image：是否使用原图
            multiimage：多图作品是否使用多图
            allowr18：是否允许R18
            allowr18g：是否允许R18G
        返回值：
            返回一个元组，由pid组成
        """
        json_result = await self.__api.user_bookmarks_illust(uid)
        func = self.__api.user_bookmarks_illust
        return await self.__illustcontent(json_result, func, *args, **kwargs)

    # 获取内容，数据处理
    @debuglog(logger)
    async def __illustcontent(
            self,
            json_result,
            func=None,
            *,
            type: str='illust',
            page: int=1,
            min_bookmarks: int=0,
            original_image: bool=False,
            multiimage: bool=False,
            allowr18: bool=False,
            allowr18g: bool=False
    ) -> tuple:
        if 'error' in json_result.keys():
            raise InfoNotFoundError
        typefilter_exclude_func = (self.__api.user_illusts, self.__api.illust_recommended, self.__api.illust_ranking)
        result = []
        _page = 1
        temp_storage = []
        first_loop = True
        get_next = False
        while _page <= page:
            while len(result) < self.__pagesize:
                if first_loop or get_next:
                    try:
                        illusts = json_result.illusts
                    except AttributeError:
                        break
                    for illust in illusts:
                        await self.__newpic(illust)
                    if type != None and func not in typefilter_exclude_func:
                        illusts = [illust for illust in illusts if illust.type==type]
                    ids = tuple([illust.id for illust in illusts if illust.total_bookmarks > min_bookmarks])
                    if not allowr18:
                        ids = self.tagfilter('R-18', ids)
                        ids = self.tagfilter('R18', ids)
                    elif not allowr18g:
                        ids = self.tagfilter('R-18G', ids)
                    first_loop = False
                else:
                    ids = []
                result.extend(temp_storage)
                result.extend(ids)
                if len(result) < self.__pagesize:
                    next_qs = self.__api.parse_qs(json_result.next_url)
                    if next_qs is None:
                        get_next = False
                        break
                    if func == self.__api.search_illust:
                        next_qs['word'] = next_qs['word'].replace('+', ' ')
                    json_result = await func(**next_qs)
                    get_next = True
                    temp_storage.clear()
                else:
                    get_next = False
                    temp_storage = result[self.__pagesize:]
            if _page < page:
                result.clear()
            _page += 1
        result = result[:self.__pagesize]
        for id in result:
            await self.__download(id, original_image, multiimage)
        if result:
            return tuple(result)
        else:
            raise InfoNotFoundError

    @debuglog(logger)
    async def __usercontent(self,
            json_result,
            func=None,
            *,
            page: int=1
        ) -> tuple:
        result = []
        _page = 1
        temp_storage = []
        first_loop = True
        get_next = False
        while _page <= page:
            while len(result) < self.__pagesize:
                if first_loop or get_next:
                    try:
                        users = json_result.user_previews
                    except AttributeError:
                        break
                    for user in users:
                        await self.__newuser(user.user)
                        [await self.__newpic(illust) for illust in user.illusts]
                    ids = tuple([user.user.id for user in users])
                    first_loop = False
                else:
                    ids = []
                result.extend(temp_storage)
                result.extend(ids)
                if len(result) < self.__pagesize:
                    next_qs = self.__api.parse_qs(json_result.next_url)
                    if next_qs is None:
                        get_next = False
                        break
                    json_result = await func(**next_qs)
                    get_next = True
                    temp_storage.clear()
                else:
                    get_next = False
                    temp_storage = result[self.__pagesize:]
            if _page < page:
                result.clear()
            _page += 1
        result = result[:self.__pagesize]
        for id in result:
            await self.__udownload(id)
        if result:
            return tuple(result)
        else:
            raise InfoNotFoundError

    # 执行下载操作并加入图库
    @debuglog(logger)
    async def __download(self, pid: int, original_image: bool=False, multiimage: bool=False):
        length = self.__data['illusts'][pid]['count'] if multiimage else 1
        type = 'original' if original_image else 'large'
        fileprefix = 'pixiv' if self.__pathflag else self.__imagepath
        for i in range(length):
            url = self.__data['illusts'][pid]['urls'][type][i]
            await self.__api.download(url, path=self.__imagepath, name=f'{pid}_{i}_{type}')
            ext = '.jpeg' if 'webp' in url or 'jpeg' in url else '.jpg' if 'jpg' in url else '.png'
            self.__data['illusts'][pid]['files'][type].append(os.path.join(fileprefix, f'{pid}_{i}_{type}' + ext))
            self.__data['illusts'][pid]['files'][type] = list(set(self.__data['illusts'][pid]['files'][type]))
            self.__data['illusts'][pid]['files'][type].sort()

    # 用户头像、横幅、工作环境图片下载并加入用户资料库
    @debuglog(logger)
    async def __udownload(self, uid: int):
        fileprefix = 'pixiv' if self.__pathflag else self.__imagepath
        try:
            url = self.__data['users'][uid]['user']['profile_image_urls']['medium']
            if url:
                await self.__api.download(url, path=self.__imagepath, name=f'u_{uid}_profile', replace=True)
                ext = '.jpeg' if 'webp' in url or 'jpeg' in url else '.jpg' if 'jpg' in url else '.png'
                self.__data['users'][uid]['user']['profile_image'] = os.path.join(fileprefix, f'u_{uid}_profile' + ext)
            else:
                self.__data['users'][uid]['user']['profile_image'] = ''
        except KeyError:
            self.__data['users'][uid]['user']['profile_image'] = ''
        if self.__data['users'][uid]['profile']:
            url = self.__data['users'][uid]['profile']['background_image_url']
            if url:
                await self.__api.download(url, path=self.__imagepath, name=f'u_{uid}_background', replace=True)
                ext = '.jpeg' if 'webp' in url or 'jpeg' in url else '.jpg' if 'jpg' in url else '.png'
                self.__data['users'][uid]['profile']['background_image'] = os.path.join(fileprefix, f'u_{uid}_background' + ext)
            else:
                self.__data['users'][uid]['profile']['background_image'] = ''
        if self.__data['users'][uid]['workspace']:
            url = self.__data['users'][uid]['workspace']['workspace_image_url']
            if url:
                await self.__api.download(url, path=self.__imagepath, name=f'u_{uid}_workspace', replace=True)
                ext = '.jpeg' if 'webp' in url or 'jpeg' in url else '.jpg' if 'jpg' in url else '.png'
                self.__data['users'][uid]['workspace']['workspace_image'] = os.path.join(fileprefix, f'u_{uid}_workspace' + ext)
            else:
                self.__data['users'][uid]['workspace']['workspace_image'] = ''

    # 图库统计
    @debuglog(logger)
    def statistics(self, only_file_exist: bool=False) -> tuple:
        '''统计本地图库的信息。
        参数：
            only_file_exist：图片统计是否仅统计已下载图片的信息。
        返回值：
            返回一个元组。
            第一个元素为图片统计，类型为字典，字段说明如下：
                total：参与统计的图片总数
                type_stat：插画与漫画数量统计
                tags_stat：标签统计
                views_stat：阅读数统计
                bookmarks_stat：收藏数统计
            第二个元素为用户统计，类型为字典，字段说明如下：
                total：参与统计的用户总数
        '''
        targetids = [k for k, v in self.__data['illusts'].items() if len(v['files']['original']) != 0 or len(v['files']['large']) != 0] \
            if only_file_exist else [k for k in self.__data['illusts'].keys()]
        totalillust = len(targetids)
        illusts_stat = {
            'total': totalillust,
            'type_stat': {'插画': 0, '漫画': 0},
            'tags_stat': {},
            'views_stat': {
                '0': {'total': totalillust, 'rate': '100%'},
                '100': {'total': 0, 'rate': ''},
                '500': {'total': 0, 'rate': ''},
                '1000': {'total': 0, 'rate': ''},
                '2000': {'total': 0, 'rate': ''},
                '5000': {'total': 0, 'rate': ''},
                '10000': {'total': 0, 'rate': ''},
                '50000': {'total': 0, 'rate': ''},
                '100000': {'total': 0, 'rate': ''},
                },
            'bookmarks_stat': {
                '0': {'total': totalillust, 'rate': '100%'},
                '100': {'total': 0, 'rate': ''},
                '500': {'total': 0, 'rate': ''},
                '1000': {'total': 0, 'rate': ''},
                '2000': {'total': 0, 'rate': ''},
                '5000': {'total': 0, 'rate': ''},
                '10000': {'total': 0, 'rate': ''},
                '50000': {'total': 0, 'rate': ''},
                '100000': {'total': 0, 'rate': ''},
                },
            }
        for id in targetids:
            item = self.__data['illusts'][id]
            # type
            if item['type'] == '插画':
                illusts_stat['type_stat']['插画'] += 1
            elif item['type'] == '漫画':
                illusts_stat['type_stat']['漫画'] += 1
            # tags
            for i in item['tags']:
                if i['name'] not in illusts_stat['tags_stat'].keys():
                    illusts_stat['tags_stat'][i['name']] = {
                        'translated_name': i['translated_name'],
                        'total': 1,
                        }
                else:
                    illusts_stat['tags_stat'][i['name']]['total'] += 1
            # views
            if item['views'] > 100000:
                illusts_stat['views_stat']['100000']['total'] += 1
            if item['views'] > 50000:
                illusts_stat['views_stat']['50000']['total'] += 1
            if item['views'] > 10000:
                illusts_stat['views_stat']['10000']['total'] += 1
            if item['views'] > 5000:
                illusts_stat['views_stat']['5000']['total'] += 1
            if item['views'] > 2000:
                illusts_stat['views_stat']['2000']['total'] += 1
            if item['views'] > 1000:
                illusts_stat['views_stat']['1000']['total'] += 1
            if item['views'] > 500:
                illusts_stat['views_stat']['500']['total'] += 1
            if item['views'] > 100:
                illusts_stat['views_stat']['100']['total'] += 1
            # bookmarks
            if item['bookmarks'] > 100000:
                illusts_stat['bookmarks_stat']['100000']['total'] += 1
            if item['bookmarks'] > 50000:
                illusts_stat['bookmarks_stat']['50000']['total'] += 1
            if item['bookmarks'] > 10000:
                illusts_stat['bookmarks_stat']['10000']['total'] += 1
            if item['bookmarks'] > 5000:
                illusts_stat['bookmarks_stat']['5000']['total'] += 1
            if item['bookmarks'] > 2000:
                illusts_stat['bookmarks_stat']['2000']['total'] += 1
            if item['bookmarks'] > 1000:
                illusts_stat['bookmarks_stat']['1000']['total'] += 1
            if item['bookmarks'] > 500:
                illusts_stat['bookmarks_stat']['500']['total'] += 1
            if item['bookmarks'] > 100:
                illusts_stat['bookmarks_stat']['100']['total'] += 1
        for k in illusts_stat['tags_stat'].keys():
            illusts_stat['tags_stat'][k]['rate'] = str(round(illusts_stat['tags_stat'][k]['total'] / totalillust * 100, 2)) + '%'
        illusts_stat['tags_stat'] = sorted([(k, v['translated_name'], v['total'], v['rate']) for k, v in illusts_stat['tags_stat'].items()], key=lambda i: i[2], reverse=True)
        for k in illusts_stat['views_stat'].keys():
            illusts_stat['views_stat'][k]['rate'] = str(round(illusts_stat['views_stat'][k]['total'] / totalillust * 100, 2)) + '%'
        for k in illusts_stat['bookmarks_stat'].keys():
            illusts_stat['bookmarks_stat'][k]['rate'] = str(round(illusts_stat['bookmarks_stat'][k]['total'] / totalillust * 100, 2)) + '%'
        users_stat = {
            'total': len(self.__data['users']),
            }
        return illusts_stat, users_stat

    # 随机图片
    @debuglog(logger)
    async def random_image(self, *, tags: tuple=None, allowr18: bool=False, allowr18g: bool=False, useb64: bool=False):
        """
        随机从本地图库中挑选图片，若本地图库无图则使用搜索功能获取图片然后挑选。
        参数：
            tags：偏好标签元组，优先从偏好标签选择
            allowr18：是否允许R18
            allowr18g：是否允许R18G
        返回值：
            file: 文件路径
            signal: 是否检索成功
        """
        if not self.__pathflag:
            useb64 = True
        if not self.__data['illusts'] or not os.listdir(self.__imagepath):
            if self.__username and self.__password:
                await self.login()
                await self.search_illust('ロリ 10000users入り')
        ids = [illust['id'] for illust in self.__data['illusts'].values() if (illust['files']['large'] or illust['files']['original']) \
            and illust['type'] == '插画']
        if not allowr18:
            ids = self.tagfilter('R-18', ids)
            ids = self.tagfilter('R18', ids)
        elif not allowr18g:
            ids = self.tagfilter('R-18G', ids)
            ids = self.tagfilter('R18G', ids)
        taggedset = []
        signal = True
        if tags:
            taggedset = []
            for tag in tags:
                taggedset.extend([id for id in ids if tag.upper() in str(self.__data['illusts'][id]['tags'])])
            if not taggedset:
                taggedset = [id for id in ids or ids if 'ロリ' in str(self.__data['illusts'][id]['tags'])]
                signal = False
            taggedset = [id for id in taggedset if self.__data['illusts'][id]['bookmarks'] > 1000] or taggedset
        else:
            taggedset = [id for id in ids if self.__data['illusts'][id]['bookmarks'] > 1000] or ids
        if taggedset:
            pid = random.choice(list(set(taggedset)))
        else:
            signal = False
            return None, signal
        file = self.__data['illusts'][pid]['files']['original'][0] if self.__data['illusts'][pid]['files']['original'] else self.__data['illusts'][pid]['files']['large'][0]
        if useb64:
            realpath = os.path.join(SIGNAL['coolq_directory'][0], 'data', 'image', file) \
                if self.__pathflag else file
            file = convert_to_b64(realpath)
        return file, signal

    # 清除缓存
    @debuglog(logger)
    def clear_cache(self):
        path = self.__imagepath
        for filepath, dirs, files in os.walk(path):
            for file in files:
                os.remove(os.path.join(filepath, file))
        for k in self.__data['illusts'].keys():
            self.__data['illusts'][k]['files']= {'original': [], 'large': []}

    # tag过滤器，滤除tag用
    @debuglog(logger)
    def tagfilter(self, tag: str, pids: tuple) -> tuple:
        return tuple([pid for pid in pids if tag not in str(self.__data['illusts'][pid]['tags'])])

class EnhancedAPI(AppPixivAPI):
    async def download(self, url, prefix='', path=os.path.curdir, fname=None, auto_ext=True,
                       name=None, replace=False, referer='https://app-api.pixiv.net/'):
        """ Override download method for using new ext sniffing method. """
        basestring = str
        if fname is None and name is None:
            name = os.path.basename(url)
        elif isinstance(fname, basestring):
            name = fname
        if name:
            img_path = os.path.join(path, prefix + name)
            if 'webp' in url or 'jpeg' in url:
                img_path = os.path.splitext(img_path)[0] + '.jpeg'
            elif 'jpg' in url:
                img_path = os.path.splitext(img_path)[0] + '.jpg'
            elif 'png' in url:
                img_path = os.path.splitext(img_path)[0] + '.png'
            if os.path.exists(img_path) and not replace:
                return False
            else:
                response, type = await self.down(url, referer)
                if 'webp' in url:
                    bytes_stream = io.BytesIO(response)
                    img = Image.open(bytes_stream)
                    img.save(img_path, format='JPEG')
                else:
                    async with aiofiles.open(img_path, mode='wb') as out_file:
                        await out_file.write(response)
        else:
            response, _ = await self.down(url, referer)
            fname.write(response)
        del response
        return True
