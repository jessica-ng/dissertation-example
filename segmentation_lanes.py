

from __future__ import absolute_import, division, print_function, unicode_literals

import tensorflow as tf

from tensorflow.tensorflow_examples.models.pix2pix import pix2pix

import tensorflow_datasets as tfds

from IPython.display import clear_output
import matplotlib
import matplotlib.pyplot as plt
import os

from dataloader import DataLoader

import numpy as np

import cv2

os.environ["CUDA_VISIBLE_DEVICES"]="-1"

#dataset, info = tfds.load('oxford_iiit_pet:3.0.0', with_info=True)

def import_data():
    IMAGE_DIR_PATH = '/home/jessica/Downloads/currentData/training/image_2'
    MASK_DIR_PATH = '/home/jessica/Downloads/currentData/training/semantic_rgb'

    # create list of PATHS
    image_paths = [os.path.join(IMAGE_DIR_PATH, x) for x in os.listdir(IMAGE_DIR_PATH) if x.endswith('.png')]
    mask_paths = [os.path.join(MASK_DIR_PATH, x) for x in os.listdir(MASK_DIR_PATH) if x.endswith('.png')]

    dataset = DataLoader(image_paths=image_paths,
                         mask_paths=mask_paths,
                         image_size=[128, 128],
                         crop_percent=None,
                         channels=[3, 3],
                         seed=47)



    dataset1 = dataset.data_batch(batch_size=100,
                                 augment = True,
                                 shuffle = True)



    train_images = []
    train_mask = []

    for image, mask in dataset1:
        train_images.append(image)
        train_mask.append(mask)

    dataset2 = DataLoader(image_paths=image_paths,
                         mask_paths=mask_paths,
                         image_size=[128, 128],
                         crop_percent=None,
                         channels=[3, 3],
                         seed=47)

    dataset2 = dataset2.data_batch(batch_size=100,
                                 augment = True,
                                 shuffle = True)

    for image, mask in dataset2:
        train_images.append(image)
        train_mask.append(mask)

    print(len(train_images[0]))
    return [train_images, train_mask]

def import_test_data():
    IMAGE_DIR_PATH = '/home/jessica/Downloads/currentData/testing/image'
    MASK_DIR_PATH = '/home/jessica/Downloads/currentData/testing/mask'

    # create list of PATHS
    image_paths = [os.path.join(IMAGE_DIR_PATH, x) for x in os.listdir(IMAGE_DIR_PATH) if x.endswith('.png')]
    mask_paths = [os.path.join(MASK_DIR_PATH, x) for x in os.listdir(MASK_DIR_PATH) if x.endswith('.png')]

    dataset = DataLoader(image_paths=image_paths,
                         mask_paths=mask_paths,
                         image_size=[128, 128],
                         crop_percent=None,
                         channels=[3, 3],
                         seed=33)

    dataset = dataset.data_batch(batch_size=100,
                                 augment=False,
                                 shuffle=False)

    test_images = []
    test_mask = []

    for image, mask in dataset:
        test_images.append(image)
        test_mask.append(mask)

    return [test_images, test_mask]

def normalize(input_image, input_mask):
  input_image = tf.cast(input_image, tf.float32) / 255.0
  input_mask -= 1
  return input_image, input_mask

@tf.function
def load_image_train(datapoint):
  input_image = tf.image.resize(datapoint['image'], (128, 128))
  input_mask = tf.image.resize(datapoint['segmentation_mask'], (128, 128))

  if tf.random.uniform(()) > 0.5:
    input_image = tf.image.flip_left_right(input_image)
    input_mask = tf.image.flip_left_right(input_mask)

  input_image, input_mask = normalize(input_image, input_mask)

  return input_image, input_mask

def load_image_test(datapoint):
  input_image = tf.image.resize(datapoint['image'], (128, 128))
  input_mask = tf.image.resize(datapoint['segmentation_mask'], (128, 128))

  input_image, input_mask = normalize(input_image, input_mask)

  return input_image, input_mask

def get_train():
    TRAIN_LENGTH = 200
    BATCH_SIZE = 200
    BUFFER_SIZE = 1000
    STEPS_PER_EPOCH = TRAIN_LENGTH // BATCH_SIZE

    # train = dataset['train'].map(train_dataset, num_parallel_calls=tf.data.experimental.AUTOTUNE)
    # test = dataset['test'].map(test_dataset)

    train_dataset = import_data()
    test_dataset = import_test_data()

    # train_dataset = train.cache().shuffle(BUFFER_SIZE).batch(BATCH_SIZE).repeat()
    # train_dataset = train_dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
    # test_dataset = test.batch(BATCH_SIZE)
    print("length", len(train_dataset[1][0]))

    return train_dataset, test_dataset, STEPS_PER_EPOCH


def display(display_list):

    plt.figure(figsize=(15, 15))
    title = ['Input Image', 'True Mask', 'Predicted Mask']
    for i in range(2):
      plt.subplot(1, len(display_list), i+1)
      plt.title(title[i])
      plt.imshow(display_list[i][0])
      plt.axis('off')

    if len(display_list) > 2:
        plt.subplot(1, len(display_list), 3)
        plt.title(title[2])
        plt.imshow(tf.keras.preprocessing.image.array_to_img(display_list[2]))
        plt.axis('off')
    plt.show()
    # print(display_list[0])
    #
    # cv2.imshow("Display window", display_list[0])
    # cv2.imshow("Display window", display_list[1])
    #
    # cv2.waitkey(0)

def show_example():
    train, test, a= get_train()

    sample_image, sample_mask = test[0][0], test[1][0]

    #sample_image = train[0]
    #sample_mask = mask[0]
    print("lol")
    display([sample_image, sample_mask])
    print("displayed")
    #print(sample_image)
    return sample_image, sample_mask

def unet_model(output_channels):

    base_model = tf.keras.applications.MobileNetV2(input_shape=[128, 128, 3], include_top=False)

    # Use the activations of these layers
    layer_names = [
        'block_1_expand_relu',  # 64x64
        'block_3_expand_relu',  # 32x32
        'block_6_expand_relu',  # 16x16
        'block_13_expand_relu',  # 8x8
        'block_16_project',  # 4x4
    ]
    layers = [base_model.get_layer(name).output for name in layer_names]

    # Create the feature extraction model
    down_stack = tf.keras.Model(inputs=base_model.input, outputs=layers)

    down_stack.trainable = False

    up_stack = [
        pix2pix.upsample(512, 3),  # 4x4 -> 8x8
        pix2pix.upsample(256, 3),  # 8x8 -> 16x16
        pix2pix.upsample(128, 3),  # 16x16 -> 32x32
        pix2pix.upsample(64, 3),  # 32x32 -> 64x64
        #pix2pix.upsample(32, 3)

    ]

    # This is the last layer of the model
    last = tf.keras.layers.Conv2DTranspose(
      output_channels, 3, strides=2,
      padding='same', activation='softmax')  #64x64 -> 128x128

    inputs = tf.keras.layers.Input(shape=[128, 128, 3])
    x = inputs

    # Downsampling through the model
    skips = down_stack(x)
    x = skips[-1]
    skips = reversed(skips[:-1])

    # Upsampling and establishing the skip connections
    for up, skip in zip(up_stack, skips):
        x = up(x)
        concat = tf.keras.layers.Concatenate()
        x = concat([x, skip])

    x = last(x)

    return tf.keras.Model(inputs=inputs, outputs=x)

def create_model():
    OUTPUT_CHANNELS = 3
    model = unet_model(OUTPUT_CHANNELS)
    model.summary()
    model.compile(optimizer='adam', loss='categorical_crossentropy',
                  metrics=['accuracy'])
    tf.keras.utils.plot_model(model, show_shapes=True)

    return model

def load_model():

    checkpoint_path = "training_lanes_1/cp.ckpt"
    checkpoint_dir = os.path.dirname(checkpoint_path)

    latest = tf.train.latest_checkpoint(checkpoint_dir)

    # Create a new model instance
    model = create_model()

    # Load the previously saved weights
    model.load_weights(latest)

    test_images, test_labels = import_test_data()

    # # Re-evaluate the model
    loss, acc = model.evaluate(test_images, test_labels, verbose=2)
    print("Restored model, accuracy: {:5.2f}%".format(100 * acc))

    return model


def create_mask(pred_mask):
    # pred_mask = tf.argmax(pred_mask, axis=-1)
    # pred_mask = pred_mask[..., tf.newaxis]
    #print(pred_mask)
    return pred_mask[0]

def show_predictions( model, dataset=None, num=1):
    sample_image, sample_mask = show_example()
    sample_image = sample_image[0,:,:,:]
    sample_image = tf.reshape(sample_image, (1,128,128,3))
    if dataset:
        for image, mask in dataset.take(num):
          pred_mask = model.predict(image)
          display([image[0], mask[0], create_mask(pred_mask)])
    else:
        display([sample_image, sample_mask,
                 create_mask(model.predict(sample_image))])

class DisplayCallback(tf.keras.callbacks.Callback):
  def on_epoch_end(self, epoch, logs=None):
    clear_output(wait=True)
    show_predictions()
    print ('\nSample Prediction after epoch {}\n'.format(epoch+1))

def train(model):
    OUTPUT_CHANNELS = 3

    base_model = tf.keras.applications.MobileNetV2(input_shape=[128, 128, 3], include_top=False)

    # Use the activations of these layers
    layer_names = [
        'block_1_expand_relu',  # 64x64
        'block_3_expand_relu',  # 32x32
        'block_6_expand_relu',  # 16x16
        'block_13_expand_relu',  # 8x8
        'block_16_project',  # 4x4
    ]
    layers = [base_model.get_layer(name).output for name in layer_names]

    # Create the feature extraction model
    down_stack = tf.keras.Model(inputs=base_model.input, outputs=layers)

    down_stack.trainable = False

    up_stack = [
        pix2pix.upsample(512, 3),  # 4x4 -> 8x8
        pix2pix.upsample(256, 3),  # 8x8 -> 16x16
        pix2pix.upsample(128, 3),  # 16x16 -> 32x32
        pix2pix.upsample(64, 3),  # 32x32 -> 64x64
        #pix2pix.upsample(32, 3),
    ]
    # show_example()
    # show_predictions()

    train_dataset, test_dataset, STEPS_PER_EPOCH = get_train()

    test_image, test_mask = show_example()

    # loss, acc = model.evaluate(test_dataset)
    # print("Restored model, accuracy: {:5.2f}%".format(100 * acc))

    checkpoint_path = "training_lanes_1/cp.ckpt"
    checkpoint_dir = os.path.dirname(checkpoint_path)

    # Create a callback that saves the model's weights
    cp_callback = tf.keras.callbacks.ModelCheckpoint(filepath=checkpoint_path,
                                                     save_weights_only=True,
                                                     verbose=1)

    #model = create_model()
    EPOCHS = 15
    VAL_SUBSPLITS = 5
    BATCH_SIZE = 200
    VALIDATION_STEPS = 100 // BATCH_SIZE // VAL_SUBSPLITS

    model_history = model.fit(train_dataset[0][0], train_dataset[1][0], epochs=EPOCHS,
                              batch_size=200,
                              steps_per_epoch=STEPS_PER_EPOCH,
                              validation_steps=VALIDATION_STEPS,
                              validation_data=(test_dataset[0][0], test_dataset[1][0]),
                              callbacks=[cp_callback])
                              #callbacks=[DisplayCallback()])

    show_predictions(model)



def main():
    model = load_model()
    get_train()
    train(model)
    #show_predictions(model)

if __name__ == "__main__":
    main()