import os.path
import requests
from urllib.parse import urlparse
import vk_api
import vk_api.exceptions
import json
import tqdm

# класс аутентификации
class VkAuth:
    def __init__(self, cl_id = "7460608"):
        self.access_token = ""

        self.clientId = cl_id
        self.scope = "photos,status"

        self.sess = None

    # провести аутентификацию
    def doAuth (self, force = False):
        # запоминание токена в файле
        if (not force and os.path.isfile ("vk.txt")):
            f = open("vk.txt", "rt")
            self.access_token = f.read().strip()
            f.close()

            # Если с прошлого раза не прошло много времени (час),
            # то токен заново получать не надо и с ним работать можно дальше
            vk = self.getApi()
            try:
                # получаем что нибудь с аккаунта (или ошибка)
                r = vk.photos.getAlbums()
            except vk_api.exceptions.ApiError as err:
                # ошибка. Надо получить токен заново
                print("Error: " + str(err.error['error_msg']))
                self.sess = None
                self.doAuth(True)
            return

        # новая аутентификация
        url = "https://oauth.vk.com/authorize?"  + \
            "client_id=" + self.clientId + \
            "&scope=" + self.scope + \
            "&response_type=token" + \
            "&redirect_uri=https://oauth.vk.com/blank.hmtl"

        print( "Пройдите по ссылке: " + url )
        print( "Подтвердите доступ" )

        res = input("И введите токен (или url подтверждения): ")

        # парсим урл и вынимаем токен
        if (res.find("access_token") > 0):
            u = urlparse(res, '', True)
            ff = u.fragment.split('&')
            for f in ff:
                np = f.split('=')
                if (np[0] == 'access_token'):
                    self.access_token = np[1]
                    break
        else:
            self.access_token = res

        # записываем обратно
        f = open("vk.txt", "wt")
        f.write(self.access_token + "\n")
        f.close()

    # получить апи для доступа
    def getApi(self):
        if (self.sess is None):
            vk_sess = vk_api.VkApi(token=self.access_token)

        vk = vk_sess.get_api()
        return vk

auth = VkAuth()
auth.doAuth()

vk = auth.getApi()

# читаем токен яндекс диска
f = open("yadisk.txt", "rt")
ya_token = f.readline()
f.close()

# ищем фотки в своем альбоме
photos = vk.photos.get( album_id='profile' )
res = []
for p in tqdm.tqdm(photos['items']):
    # p = photos['items'][i]

    # print( p )

    # ищем макс размер
    s_url = ""
    max_w = 0
    for s in p['sizes']:
        if (max_w < s['width']):
            max_w = s['width']
            s_url = s['url']

    # берем пост с лайками
    post_id = "%d_%d" % (p['owner_id'], p['post_id'])
    w = vk.wall.getById(posts=post_id)

    # print( w )

    likes = 0
    # [{'id': 1166, 'from_id': 29897474, 'owner_id': 29897474, 'date': 1305833439, 'can_delete': 1, 'is_favorite': False, 'is_deleted': True, 'text': 'Запись удалена ', 'deleted_reason': 'Запись удалена', 'deleted_details': ''}]
    if ('is_deleted' not in w[0]) or (not w[0]['is_deleted']):
        likes = w[0]['likes']['count']

    # print( "  max width %d likes %d and url %s" % (max_w, likes, s_url) )

    # формируем запрос на загрузку
    arg = {'path': str(likes) + ".jpg",
            'url': s_url}
    headers = {'Authorization': 'OAuth ' + ya_token}

    # загружаем
    requests.post("https://cloud-api.yandex.net" +
                   "/v1/disk/resources/upload", params=arg, headers=headers)

    arg['likes'] = likes

    res.append(arg)

f = open("res.json", "wt")
f.write(json.dumps(res, indent=4))
f.close()

print("Done")
