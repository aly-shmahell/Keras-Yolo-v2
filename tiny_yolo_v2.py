from keras.models import Sequential
from keras.layers import Conv2D, BatchNormalization, LeakyReLU, MaxPooling2D, InputLayer, Input
from keras import backend as K
from keras import Model

from darknet_weight_loader import load_weights

import tensorflow as tf
from classifcation_utils import non_max_suppression
from yolov2_tools import getClassInterestConf, getBoundingBoxesFromNetOutput
import numpy as np

# 6 x (conv - bn - leakyrelu - maxpool) + 2 * (conv - bn - leakyrelu)
# layer_indices = [0, 4, 8, 12, 16, 20, 24, 27]

def conv_batch_lrelu(input_tensor, numfilter, dim):
    input_tensor = Conv2D(numfilter, (dim, dim), padding='same')(input_tensor)
    input_tensor = BatchNormalization()(input_tensor)
    return LeakyReLU(alpha=0.1)(input_tensor)

TINY_YOLOV2_ANCHOR_PRIORS = np.array([
    1.08, 1.19, 3.42, 4.41, 6.63, 11.38, 9.42, 5.11, 16.62, 10.52
]).reshape(5, 2)

class TinyYOLOv2:
    def __init__(self, image_size):
        K.set_learning_phase(0)
        K.reset_uids()

        self.image_size = image_size

        self.m = self.buildModel()
        self.has_weights = False

    def loadWeightsFromDarknet(self, file_path):
        load_weights(self.m, file_path)
        self.has_weights = True

    def loadWeightsFromKeras(self, file_path):
        self.m.load_weights(file_path)
        self.has_weights = True

    def buildModel(self):
        model_in = Input((self.image_size, self.image_size, 3))
        
        model = model_in
        for i in range(0, 5):
            model = conv_batch_lrelu(model, 16 * 2**i, 3)
            model = MaxPooling2D(2, padding='valid')(model)

        model = conv_batch_lrelu(model, 512, 3)
        model = MaxPooling2D(2, 1, padding='same')(model)

        model = conv_batch_lrelu(model, 1024, 3)
        model = conv_batch_lrelu(model, 1024, 3)
        
        model_out = Conv2D(125, (1, 1), padding='same', activation='linear')(model)
        return Model(inputs=model_in, outputs=model_out)

    def forward(self, images):
        if not self.has_weights:
            raise ValueError("Network needs to be initialised before being executed")

        if len(images.shape) == 3:
            # single image
            images = images[None]

        output = self.m.predict(images).reshape(
            -1, self.image_size // 32, self.image_size // 32, 5, 25)

        allboxes = []
        for o in output:
            out = getClassInterestConf(o, 14) # people class
            boxes = getBoundingBoxesFromNetOutput(out, TINY_YOLOV2_ANCHOR_PRIORS, confidence_threshold=0.3)
            allboxes.append(non_max_suppression(boxes, 0.3))

        return allboxes




    