from time import sleep
import threading
import json
import paho.mqtt.client as mqtt

import signal
import time

import io
from PIL import Image
import base64
import cStringIO


try:
    from picamera import PiCamera
except Exception:
    pass


class CoreService(object):
    _kill_now = False

    _comm_client = None
    _comm_delay = 0
    _thread_comms = None
    _thread_lock = None

    _camera = None

    _system_channel = '/system'
    _data_channel = '/camera/rpi'


    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def start(self):
        self._comm_client = mqtt.Client(
            client_id="service_camera_rpi",
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
            self._camera = PiCamera()
            # self._camera.iso = 100
            # sleep(2) # give lens time to adjust
            # self._camera.shutter_speed = self._camera.exposure_speed
            # self._camera.shutter_speed = 100000
            # self._camera.exposure_mode = 'off'
            # g = self._camera.awb_gains
            # self._camera.awb_mode = 'off'
            # self.awb_gains = g

            PiCamera.CAPTURE_TIMEOUT = 10

        except Exception as e:
            self._camera = None
            print(e)

        while True:
            if self._camera:
                print("[CAMERA-RPI] Starting filestream.")

                # Capture raw camera image and create a PIL image object

                stream = io.BytesIO()
                image = None
                img_str = None
                buffer = None

                print("[CAMERA-RPI] Taking a photo..")

                try:
                    # self._camera.start_preview()
                    time.sleep(2)
                    self._camera.capture(stream, format='jpeg')

                    stream.seek(0)
                    image = Image.open(stream)

                    buffer = cStringIO.StringIO()
                    image.save(buffer, format='JPEG')
                    img_str = base64.b64encode(buffer.getvalue())

                except Exception as e:
                    print("[TURING-CAMERA-RPI] Had an issue capturing a photo: %s" % e)

                try:
                    self.output(img_str, self._data_channel)

                except Exception as e:
                    print("[TURING-CAMERA-RPI] Couldn't publish to comms")

            else:
                print("[CAMERA-RPI] Skipping taking a photo. Not a supported OS.")

            time.sleep(10)

            if self._kill_now:
                self._camera.close()
                break

    def _on_connect(self, client, userdata, flags, rc):
        self.output('{"sender": "service_camera_rpi", "message": "Connected to GrandCentral."}')

    def _on_message(self, client, userdata, msg):
        msg_struct = None

        try:
            msg_struct = json.loads(msg.payload)

        except:
            pass

    def _on_publish(self, mosq, obj, mid):
        pass

    def _on_subscribe(self, mosq, obj, mid, granted_qos):
        self.output('{"sender": "service_camera_rpi", "message": "Successfully subscribed to GrandCentral /system channel."}')

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

        except Exception, e:
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
