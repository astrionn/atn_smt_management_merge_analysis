import requests



def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            #print(e)
            return False
    return wrapper


class NeolightHandler():

    def __init__(self, url : str, port : int) -> None:
        self.url = 'http://' + url + ':' + str(port) + '/'
        self.headers = {'content-type': 'application/json'}
        self.on_leds = []
        # self.redis_cli = redis.Redis(host='localhost', port=6379, db=0)

    @handle_errors
    def tower_on(self, tower : int, color : str) -> str:
        """
        Turn on tower light
        :param tower: tower number (1,2)
        :param color: color of the light (red, green, yellow)
        :return: response
        """
        if tower == 1:
            tower_name = 'channel1'
        elif tower == 2:
            tower_name = 'channel2'
        else: 
            return 'Invalid tower number'
            
        if color not in ['red', 'green',  'yellow']:
            return 'Invalid color'

        data = {'workchannel': tower_name, 'workcolor': color}

        resp = requests.post(self.url + 'workinglight', json=data, headers=self.headers,timeout=0.2)
        return resp.text

    @handle_errors
    def tower_off(self, tower : int, color : str) -> str:
        """
        Turn off tower light
        :param tower: tower number (1,2)
        :param color: color of the light (red, green, yellow)
        :return: response
        """
        if tower == 1:
            tower_name = 'channel1'
        elif tower == 2:
            tower_name = 'channel2'
        else: 
            return 'Invalid tower number'
            
        if color not in ['red', 'green',  'yellow']:
            return 'Invalid color'

        data = {'workchannel': tower_name, 'workcolor': color}
        resp = requests.post(self.url + 'workingoff', json=data, headers=self.headers)
        return resp.text

    @handle_errors
    def led_on(self, num : str , color : str) -> str:
        """
        Turn on led light
        :param num: led number (1,2,3,4)
        :param color: color of the light (red, green, yellow)
        :return: response
        """       
        if color not in ['red', 'green', 'yellow', 'blue']:
            return 'Invalid color'

        data = {'light_led': num, 'light_led_color': color}
        resp = requests.post(self.url + 'ledopen', json=data, headers=self.headers)
        self.on_leds.append(num)
        return resp.text

    @handle_errors
    def led_off(self, num : str) -> str:
        """
        Turn off led light
        :param num: led number (1,2,3,4)
        :return: response
        """
        data = {'off_led': num}
        resp = requests.post(self.url + 'ledoff', json=data, headers=self.headers)
        self.on_leds.remove(num)
        return resp.text

    @handle_errors
    def side_on(self, side : int ,color : str) -> str:
        """
        Turn on all leds
        :param color: color of the light (red, green, yellow)
        :return: response
        """
        if side == 1:
            side_name = 'channel1'
        elif side == 2:
            side_name = 'channel2'
        else: 
            return 'Invalid tower number'

        if color not in ['red', 'green', 'yellow', 'blue']:
            return 'Invalid color'

        data = {'channel_num' : side_name  ,'channel_color': color}
        resp = requests.post(self.url + 'lineledon', json=data, headers=self.headers)
        return resp.text

    @handle_errors
    def side_off(self, side : int) -> str:
        """
        Turn off all leds
        :return: response
        """
        if side == 1:
            side_name = 'channel1'
        elif side == 2:
            side_name = 'channel2'
        else: 
            return 'Invalid tower number'

        data = {'channel_num' : side_name, 'channel_color': 'blue'}
        resp = requests.post(self.url + 'lineledoff', json=data, headers=self.headers)
        return resp.text

    @handle_errors
    def reset_leds(self) -> str:
        """
        Turn off all leds
        :return: response
        """
        for led in self.on_leds:
            self.led_off(led)
