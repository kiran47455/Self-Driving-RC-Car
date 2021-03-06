import numpy as np
import cv2
import socket
from getKeys import key_check
import requests
import urllib3
import json

class StreamingServer(object):
    def __init__(self):
        self.restUrl = 'http://192.168.1.106:8080/control'
        # self.restUrl = 'http://192.168.1.106:5000/messages'
        self.server_socket = socket.socket()
        self.server_socket.bind(('192.168.1.102', 8000))
        self.server_socket.listen(1)
        self.conn, self.client_address = self.server_socket.accept()
        self.connection = self.conn.makefile('rb')

        # create labels
        self.k = np.zeros((4, 4), 'float')
        for i in range(4):
            self.k[i, i] = 1
        self.temp_label = np.zeros((1, 4), 'float')
        self.streamingAndCollectData()

    def streamingAndCollectData(self):
        saved_frame = 0
        total_frame = 0

        # collect images for training
        print('Start collecting images...')
        e1 = cv2.getTickCount()
        image_array = np.zeros((1, 38400))
        label_array = np.zeros((1, 4), 'float')

        try:
            print("Connection from: ", self.client_address)
            print("Streaming...")
            print("Press 'Q' to exit")

            stream_bytes = b''
            frame = 1
            while True:
                stream_bytes += self.connection.read(1024)
                first = stream_bytes.find(b'\xff\xd8')
                last = stream_bytes.find(b'\xff\xd9')
                self.conn.sendall(b'WA')
                if first != -1 and last != -1:
                    jpg = stream_bytes[first:last + 2]
                    stream_bytes = stream_bytes[last + 2:]
                    image = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    height, width = image.shape
                    # select lower half of the image
                    roi = image[int(height/2):height, :]
                    # select lower half of the image
                    # cv2.imshow('image', roi)
                    
                    # save streamed images
                    cv2.imwrite('training_images/Imageframe{:>05}.jpg'.format(frame), roi)
                    # reshape the roi image into one row array
                    # temp_array = roi.reshape(1, 38400).astype(np.float32)
                    temp_array = roi.flatten().astype(np.float32)
                    frame += 1
                    total_frame += 1

                    # Check key stroke while streaming
                    keys = key_check()

                    if 'W' in keys and 'A' in keys:
                        print("Forward Left")
                        image_array = np.vstack((image_array, temp_array))
                        # Remember to check label_array later
                        label_array = np.vstack((label_array, self.k[0]))
                        saved_frame += 1

                        # Send key to rest api
                        payload = dict(data='WA')
                        response = requests.post(self.restUrl, data=payload)
                        print(response, payload, 'sent to server.')

                    elif 'W' in keys and 'D' in keys:
                        print("Forward Right")
                        image_array = np.vstack((image_array, temp_array))
                        label_array = np.vstack((label_array, self.k[1]))
                        saved_frame += 1

                        # Send key to rest api
                        payload = dict(data='WD')
                        headers = { 'content-type': 'application/json' }
                        response = requests.post(self.restUrl, data=json.dumps(payload), headers=headers )
                        print(response, payload, 'sent to server.')
                        

                    elif 'S' in keys and 'A' in keys:
                        print("Reverse Left")

                        # Send key to rest api
                        payload = dict(data='SA')
                        response = requests.post(self.restUrl, data=payload)
                        print(response, payload, 'sent to server.')
                        

                    elif 'S' in keys and 'D' in keys:
                        print("Reverse Right")

                        # Send key to rest api
                        payload = dict(data='SD')
                        response = requests.post(self.restUrl, data=payload)
                        print(response, payload, 'sent to server.')
                        

                    elif 'W' in keys:
                        print("Forward")
                        saved_frame += 1
                        image_array = np.vstack((image_array, temp_array))
                        label_array = np.vstack((label_array, self.k[2]))

                        # Send key to rest api
                        payload = dict(data='W')
                        response = requests.post(self.restUrl, data=payload)
                        print(response, payload, 'sent to server.')

                    elif 'S' in keys:
                        print("Reverse")
                        saved_frame += 1
                        image_array = np.vstack((image_array, temp_array))
                        label_array = np.vstack((label_array, self.k[3]))
                        
                        # Send key to rest api
                        payload = dict(data='S')
                        response = requests.post(self.restUrl, data=payload)
                        print(response, payload, 'sent to server.')

                    elif 'D' in keys:
                        print("Right")
                        saved_frame += 1
                        image_array = np.vstack((image_array, temp_array))
                        label_array = np.vstack((label_array, self.k[1]))
                        
                        # Send key to rest api
                        payload = dict(data='D')
                        response = requests.post(self.restUrl, data=payload)
                        print(response, payload, 'sent to server.')


                    elif 'A' in keys:
                        print("Left")
                        saved_frame += 1
                        image_array = np.vstack((image_array, temp_array))
                        label_array = np.vstack((label_array, self.k[0]))
                        
                        # Send key to rest api
                        payload = dict(data='A')
                        response = requests.post(self.restUrl, data=payload)
                        print(response, payload, 'sent to server.')

                    elif 'Q' in keys:
                        print('exit')
                        self.send_inst = False
                        
                        # Send key to rest api
                        payload = dict(data='Q')
                        response = requests.post(self.restUrl, data=payload)
                        print(response, payload, 'sent to server.')

                        break

            # save training images and labels
            train = image_array[1:, :]
            train_labels = label_array[1:, :]

            # save training data as a numpy file
            np.savez('training_data_temp/test00001.npz', train=train, train_labels=train_labels)

            e2 = cv2.getTickCount()
            # calculate streaming duration
            time0 = (e2 - e1) / cv2.getTickFrequency()
            print('Streaming duration:', time0)

            print(train.shape)
            print(train_labels.shape)
            print('Total frame:', total_frame)
            print('Saved frame:', saved_frame)
            print('Dropped frame', total_frame - saved_frame)
            
        finally:
            self.connection.close()
            self.server_socket.close()

if __name__ == '__main__':
    StreamingServer()