import paho.mqtt.client as mqtt
import argparse
import configparser
import datetime
import requests
import os

sonos_api_url = 'http://docker.moik.org:5005/'
switcher = {
                "FF6897": "wohnzimmer/linein",	# button '0'
                "FF30CF": "",	# button '1'
                "FF18E7": "ircode/2",	# button '2'
                "FF7A85": "ircode/3",	# button '3'
                "FF10EF": "ircode/4",	# button '4'
                "FF38C7": "ircode/5",	# button '5'
                "FF5AA5": "wohnzimmer/favorite/181.FM%20The%20Point",	# button '6'
                "FF42BD": "wohnzimmer/favorite/181.FM%20Chilled%20Out",	# button '7'
                "FF4AB5": "",	# button '8'
                "FF52AD": "wohnzimmer/favorite/Radio%20Swiss%20Pop",	# button '9'
                "FFA857": "wohnzimmer/volume/+3",	# button '+'
                "FFE01F": "wohnzimmer/volume/-3",	# button '-'
                "FFC23D": "wohnzimmer/playpause",	# button 'Play/Pause'
}

def configSectionMap(config, section):
    dict1 = {}
    options = config.options(section)
    for option in options:
        try:
            dict1[option] = config.get(section, option)
            if dict1[option] == -1:
                print("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1



def parseTheArgs() -> object:
    parser = argparse.ArgumentParser(description='Listen to specific messages on MQTT and fire the API call')
    parser.add_argument('-d', dest='verbose', action='store_true',
                        help='print debugging information')
    parser.add_argument('-f', help='path and filename of the config file, default is ./config.rc',
                        default='/code/config.rc')

    args = parser.parse_args()
    return args


# The  callback for the ir data
def callback_irdata(client, userdata, message):
    print("Received direct message @ " + str(datetime.datetime.now()) + " : (" + str(message.payload) + ") on topic '"
          + message.topic + "' with QoS " + str(message.qos))

    # remove leading 2 bytes and tail 1 byte
    message_str=str(message.payload)[2:]
    message_str=message_str[:-1]
    message_dict=str(message_str).split(',')
    if message_dict[0] == '3' and message_dict[2] == '32':

        cmd = switcher.get(message_dict[1], "unknown")
        if cmd != "unknown":
            cmd = sonos_api_url + cmd
            print("Sending the following request: ", cmd)
            r = requests.get(cmd)
            if r.status_code != 200:
                print("Error in communication with SonosAPI. HTTP Error code: ", r.status_code)
        elif message_dict[1] == "FFE21D":
            # CH+ --> toggle the anker light
            r = requests.get('http://mystromrestapi.moik.org:5001/light')
            if r.status_code != 200:
                print("Error in communication with SonosAPI. HTTP Error code: ", r.status_code)
        else:
            print("This IR code is not yet programmed")
            print(message_dict[1])


def on_connect(client, userdata, rc):
    print("connecting reason  "  +str(rc))

def on_disconnect(client, userdata, rc):
    print("disconnected! Reason :" + str(rc))
    print("  user data: " + str(userdata))
    # try to reconnect 10 times, then die
    sleep(10)
    print("try to reconnect")
    client.reconnect()


def main():
    args = parseTheArgs()
    config = configparser.ConfigParser()
    config.read(args.f)

    try:
        broker = configSectionMap(config, "MQTT")['host']
    except:
        print("Could not open config file, or could not find config section in file")
        config_full_path = os.getcwd() + "/" + args.f
        print("Tried to open the config file: ", config_full_path)

        return 1
    # get the client name from the config map

    client = mqtt.Client(configSectionMap(config, "MQTT")['client_name'])


    #######Bind function to callback
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    print("connecting to broker ", broker)
    client.username_pw_set(configSectionMap(config, "MQTT")['username'], configSectionMap(config, "MQTT")['password'])
    # todo: try catch .... if the broker can not be connected
    try:
        client.connect(broker)
    except:
        print("ERROR: Can not connect to MQTT broker")
        return 1


    # subscribe
    print("subscribing ")
    client.message_callback_add("ir/sender",callback_irdata)

    client.subscribe([("ir/sender", 0), ])

    # the loop_forever cope also with reconnecting if needed
    client.loop_forever()


# this is the standard boilerplate that calls the main() function
if __name__ == '__main__':
    # sys.exit(main(sys.argv)) # used to give a better look to exists
    main()
