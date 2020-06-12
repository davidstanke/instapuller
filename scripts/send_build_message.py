from httplib2 import Http
from json import dumps


#
# Hangouts Chat incoming webhook quickstart
#
def main():
    url = 'https://chat.googleapis.com/v1/spaces/AAAAn4yZytI/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=u4jlIHJF6XXsAE0ej3pW1NsajKQdT13YkaxgNSKiKBU%3D'
    bot_message = {
        'text': '<https://instapuller.serverlessux.design/stats|Insta-puller> has just built and released successfully.'}

    message_headers = {'Content-Type': 'application/json; charset=UTF-8'}

    http_obj = Http()

    response = http_obj.request(
        uri=url,
        method='POST',
        headers=message_headers,
        body=dumps(bot_message),
    )

    print(response)


if __name__ == '__main__':
    main()
