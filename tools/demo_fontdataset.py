#!/usr/bin/env python

# --------------------------------------------------------
# Tensorflow Faster R-CNN
# Licensed under The MIT License [see LICENSE for details]
# Written by Xinlei Chen, based on code from Ross Girshick
# --------------------------------------------------------

"""
Demo script showing detections in sample images.

See README.md for installation instructions before running.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import _init_paths
from model.config import cfg
from model.test import im_detect
from model.nms_wrapper import nms

from utils.timer import Timer
import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import os, cv2
import argparse

import xml.etree.ElementTree as ET

from nets.vgg16 import vgg16
from nets.resnet_v1 import resnetv1

from datasets.factory import get_imdb

from PIL import Image, ImageFont, ImageDraw

NETS = {'vgg16': ('vgg16_faster_rcnn_iter_70000.ckpt',),'res101': ('res101_faster_rcnn_iter_110000.ckpt',)}
DATASETS= {
    'fontdataset': ('fontdataset_trainval',),
    'fontdataset_test': ('fontdataset_test',),
    'pascal_voc': ('voc_2007_trainval',),
    'pascal_voc_0712': ('voc_2007_trainval+voc_2012_trainval',)
}

def parse_rec(filename):
    """ Parse a PASCAL VOC xml file """
    tree = ET.parse(filename)
    objects = []
    for obj in tree.findall('object'):
        obj_struct = {}
        obj_struct['name'] = obj.find('name').text
        # obj_struct['pose'] = obj.find('pose').text
        # obj_struct['truncated'] = int(obj.find('truncated').text)
        # obj_struct['difficult'] = int(obj.find('difficult').text)
        obj_struct['pose'] = ''
        obj_struct['truncated'] = 0
        obj_struct['difficult'] = 0
        bbox = obj.find('bndbox')
        obj_struct['bbox'] = [int(bbox.find('xmin').text),
                              int(bbox.find('ymin').text),
                              int(bbox.find('xmax').text),
                              int(bbox.find('ymax').text)]
        objects.append(obj_struct)

    return objects


def vis_detections(pil_im, class_name, dets, thresh=0.5):
    """Draw detected bounding boxes."""
    inds = np.where(dets[:, -1] >= thresh)[0]
    if len(inds) == 0:
        return list()


    boxes = list()
    draw = ImageDraw.Draw(pil_im)
    #font = ImageFont.truetype(os.path.join(cfg.DATA_DIR, 'Ubuntu.ttf'), 14)
    font = ImageFont.truetype('/usr/share/fonts/truetype/nanum/NanumGothic_Coding.ttf', 14)
    for i in inds:
        bbox = dets[i, :4]
        score = dets[i, -1]

        draw.rectangle([(int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3]))],
                       fill=None,
                       outline=(255, 0, 0)
                       )
        draw.text((int(bbox[0]) - 2, int(bbox[1]) - 15),
                  # '{:s} {:.3f}'.format(str(class_name.encode('utf-8')), score),
                  # class_name + u' ' + unicode(str(score)),
                  class_name + u' ' + u'{:.2f}'.format(score),
                  font=font,
                  fill=(0, 0, 255),
                  encoding='utf-8'
                  )

        boxes.append([
            int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]), score, class_name
        ])

    del draw

    return boxes


def compare_founding(found_boxes, answer):
    '''

    :param found_boxes:
    :param answer:
    :return:
    '''
    pass

def demo(sess, net, image_name, imdb, testimg):
    """Detect object classes in an image using pre-computed object proposals."""

    # Load the demo image
    # im_file = os.path.join(cfg.DATA_DIR, 'demo', image_name)
    im_file = os.path.join(testimg, 'images', image_name)
    anno_file = os.path.join(testimg, 'annotations', image_name.split('.')[0], '.xml')
    print(im_file, anno_file)
    im = cv2.imread(im_file)

    # Detect all object classes and regress object bounds
    timer = Timer()
    timer.tic()
    scores, boxes = im_detect(sess, net, im)
    timer.toc()
    print('Detection took {:.3f}s for {:d} object proposals'.format(timer.total_time, boxes.shape[0]))

    pil_im = Image.open(im_file)

    CLASSES = imdb.classes
    # Visualize detections for each class
    CONF_THRESH = 0.8
    NMS_THRESH = 0.3

    found_boxes = list()

    for cls_ind, cls in enumerate(CLASSES[1:]):
        cls_ind += 1 # because we skipped background
        cls_boxes = boxes[:, 4*cls_ind:4*(cls_ind + 1)]
        cls_scores = scores[:, cls_ind]
        dets = np.hstack((cls_boxes,
                          cls_scores[:, np.newaxis])).astype(np.float32)
        keep = nms(dets, NMS_THRESH)
        dets = dets[keep, :]
        found_boxes += vis_detections(pil_im, cls, dets, thresh=CONF_THRESH)

    result_file = os.path.join(testimg, 'result', image_name.split('.')[0] + '_result.jpg')
    pil_im.save(result_file)

    print(found_boxes)

    answer = parse_rec(anno_file)
    compare_founding(found_boxes, answer)

def parse_args():
    """Parse input arguments."""
    parser = argparse.ArgumentParser(description='Tensorflow Faster R-CNN demo')
    parser.add_argument('--net', dest='demo_net', help='Network to use [vgg16 res101]',
                        choices=NETS.keys(), default='res101')
    parser.add_argument('--dataset', dest='dataset', help='Trained dataset [pascal_voc pascal_voc_0712]',
                        choices=DATASETS.keys(), default='pascal_voc_0712')
    parser.add_argument('--index', dest='index', help='Index list file name',
                        default=' ')
    parser.add_argument('--testimg', dest='testimg', help='Testing images: foler names',
                        default='demo')
    parser.add_argument('--model', dest='model', help='Trained model file name',
                        default=' ')
    args = parser.parse_args()

    return args

if __name__ == '__main__':
    cfg.TEST.HAS_RPN = True  # Use RPN for proposals
    args = parse_args()

    # model path
    demonet = args.demo_net
    dataset = args.dataset
    tfmodel = args.model
    index_file = args.index

    testimg = args.testimg
    print(testimg)

    if not os.path.isfile(tfmodel + '.meta'):
        raise IOError(('{:s} not found.\nDid you download the proper networks from '
                       'our server and place them properly?').format(tfmodel + '.meta'))

    # set config
    tfconfig = tf.ConfigProto(allow_soft_placement=True)
    tfconfig.gpu_options.allow_growth=True

    # init session
    sess = tf.Session(config=tfconfig)

    # load dataset
    imdb = get_imdb(dataset)

    # load network
    if demonet == 'vgg16':
        net = vgg16()
    elif demonet == 'res101':
        net = resnetv1(num_layers=101)
    else:
        raise NotImplementedError
    net.create_architecture("TEST", imdb.num_classes,
                          tag='default', anchor_scales=[8, 16, 32])
    saver = tf.train.Saver()
    saver.restore(sess, tfmodel)

    print('Loaded network {:s}'.format(tfmodel))

    # im_names = ['000456.jpg', '000542.jpg', '001150.jpg',
    #             '001763.jpg', '004545.jpg']

    #im_names = [str(x) + '.png' for x in range(50)]
    # im_names = [str(x) + '.png' for x in range(8000)]

    with open(index_file, 'r') as f:
        lines = f.readlines()
        im_names = [x.strip() + '.png' for x in lines]

    for im_name in im_names:
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        print('Demo for {}/{}'.format(testimg, im_name))
        demo(sess, net, im_name, imdb, testimg)

    # plt.show()