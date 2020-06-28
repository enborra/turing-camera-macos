from time import sleep
import threading
import json
import paho.mqtt.client as mqtt

import signal
import time

import io
from PIL import Image
import base64
from io import StringIO
import cv2


class CoreService(object):
    _kill_now = False

    _comm_client = None
    _comm_delay = 0
    _thread_comms = None
    _thread_lock = None

    _camera = None

    _system_channel = '/system'
    _data_channel = '/camera/macos'


    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def start(self):
        self._comm_client = mqtt.Client(
            client_id="service_camera_macos",
            clean_session=True
        )

        self._comm_client.on_message = self._on_message
        self._comm_client.on_connect = self._on_connect
        self._comm_client.on_publish = self._on_publish
        self._comm_client.on_subscribe = self._on_subscribe

        self._thread_lock = threading.RLock()

        self._thread_comms = threading.Thread(target=self._start_thread_comms)
        self._thread_comms.setDaemon(True)
        self._thread_comms.start()

        try:
            pass

        except Exception as e:
            self._camera = None
            print(e)

        # define a video capture object
        self._camera = cv2.VideoCapture(0)

        while True:
            if self._camera:
                print("[CAMERA-MACOS] Starting filestream.")

                stream = io.BytesIO()
                image = None
                img_str = None
                buf = None

                print("[CAMERA-MACOS] Taking a photo..")

                try:
                    time.sleep(2)

                    # Capture raw camera image and create a PIL image object
                    ret, frame = self._camera.read()
                    is_success, buffer = cv2.imencode(".jpg", frame)
                    stream = io.BytesIO(buffer)

                    img_str = base64.b64encode(buffer)

                except Exception as e:
                    print("[TURING-CAMERA-MACOS] Had an issue capturing a photo: %s" % e)

                try:
                    self.output(img_str, self._data_channel)

                except Exception as e:
                    print("[TURING-CAMERA-MACOS] Couldn't publish to comms")

            else:
                print("[CAMERA-MACOS] Skipping taking a photo. Not a supported OS.")

            time.sleep(10)

            if self._kill_now:
                # After the loop release the cap object
                self._camera.release()
                # Destroy all the windows
                cv2.destroyAllWindows()


                # self._camera.close()
                break

    def _on_connect(self, client, userdata, flags, rc):
        self.output('{"sender": "service_camera_macos", "message": "Connected to GrandCentral."}')

    def _on_message(self, client, userdata, msg):
        msg_struct = None

        try:
            msg_struct = json.loads(msg.payload)

        except:
            pass

    def _on_publish(self, mosq, obj, mid):
        pass

    def _on_subscribe(self, mosq, obj, mid, granted_qos):
        self.output('{"sender": "service_camera_macos", "message": "Successfully subscribed to GrandCentral /system channel."}')

    def _on_log(self, mosq, obj, level, string):
        pass

    def _connect_to_comms(self):
        print('Connecting to comms system..')

        try:
            self._comm_client.connect(
                'localhost',
                1883,
                60
            )

        except Exception as e:
            print('Could not connect to local GranCentral. Retry in one second.')

            time.sleep(1)
            self._connect_to_comms()

    def _start_thread_comms(self):
        print('Comms thread started.')

        self._thread_lock.acquire()

        try:
            self._connect_to_comms()

        finally:
            self._thread_lock.release()

        print('Connected to comms server.')

        while True:
            self._thread_lock.acquire()

            try:
                if self._comm_delay > 2000:
                    self._comm_client.loop()
                    self._comm_delay = 0

                else:
                    self._comm_delay += 1

            finally:
                self._thread_lock.release()

    def output(self, msg, channel=_system_channel):
        if self._comm_client:
            self._comm_client.publish(channel, msg)

    def stop(self):
        pass

    def exit_gracefully(self,signum, frame):
        self._kill_now = True
