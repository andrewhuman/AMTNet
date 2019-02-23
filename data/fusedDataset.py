"""UCF24 Dataset Classes

Original author: Francisco Massa for VOC dataset
https://github.com/fmassa/vision/blob/voc_dataset/torchvision/datasets/voc.py
Updated by: Ellis Brown, Max deGroot for VOC dataset

Updated by Gurkirt Singh for ucf101-24 dataset
"""

import os, pdb
import torch
import torch.utils.data as data
import cv2, pickle
import numpy as np
from shared import CLASSES

np.random.seed(123)


class ActionDetection(data.Dataset):

    def __init__(self, args, image_set, transform=None, target_transform=None, split=1, full_test=False):

        self.seq_len = args.seq_len
        self.seq_gap = args.seq_gap
        self.dataset =args.dataset
        if full_test:
            seq_gap = args.eval_gap
        else:
            seq_gap = args.seq_gap
        self.input_type_rgb = args.input_type_rgb +'-images'
        self.input_type_flow = args.input_type_flow + '-images'
        self.input_frames_rgb = args.input_frames_rgb
        self.input_frames_flow = args.input_frames_flow

        self.fusion = True

        if args.fusion_type in ['rgb','flow']:
            self.fusion = False
            if args.fusion_type in ['rgb']
                self.input_type_rgb = args.input_type_rgb +'-images'
                self.input_frames_rgb = args.input_frames_rgb
            else:
                self.input_type_rgb = args.input_type_flow + '-images'
                self.input_frames_rgb = args.input_frames_flow

        

        self.root = args.data_root
        self.CLASSES = CLASSES[args.dataset]
        self.num_classes = len(CLASSES)
        self.image_set = image_set
        self.transform = transform
        self.target_transform = target_transform
        self.name = args.dataset
        self.ids = list()

        trainlist, testlist, video_list, numf_list, self.print_str = make_lists(args.dataset, self.root, self.input_type_rgb, seq_len=self.seq_len,
                                                     seq_gap=seq_gap, split=split, fulltest=full_test, imgs = image_set)
        self.video_list = video_list
        self.numf_list = numf_list
        if self.image_set == 'train':
            self.ids = trainlist
        elif self.image_set == 'test':
            self.ids = testlist
        else:
            print('spacify correct subset ')

    def __getitem__(self, index):
        rgb, flow, gt, nmt, img_index = self.pull_item(index)

        return rgb, flow, gt, nmt, img_index

    def __len__(self):
        return len(self.ids)

    def pull_item(self, index):
        annot_info = self.ids[index]
        actVidName = self.video_list[annot_info[0]]
        frm_nos = annot_info[1] + 1
        # print(frm_nos,self.seq_len)
        assert (len(frm_nos) == self.seq_len)
        labels = annot_info[2]
        gtbxs = annot_info[3]  # boxes are in xmin ymin width and height format
        # print(gtbxs)
        num_mt = len(labels)
        numf = self.numf_list[annot_info[0]]

        '''**********   Load RGb *********'''
        num_input_frames = self.input_frames_rgb
        all_frames_ids =[]
        first_index = []
        count = 0

        # print(frm_nos, actVidName)
        for fn in frm_nos:
            if numf+1 <= fn + num_input_frames//2 + 1:
                ef = min(numf+1, fn + num_input_frames//2 + 1)
                sf = ef-num_input_frames
            else:
                sf = max(fn - num_input_frames//2, 1)
                ef = sf+num_input_frames
            frames_ids = np.arange(sf,ef)
            c = 0
            for f in frames_ids:
                if f not in all_frames_ids:
                    all_frames_ids.append(f)
                    c+=1
            if count == 0:
                first_index.append(0)
            else:
                first_index.append(c)
                first_index[count] += first_index[count-1]
            count += 1

        img_path = '{}{}/{}'.format(self.root,self.input_type_rgb, actVidName)

        imgs = []

        for fn in all_frames_ids:
            img_file = '{:s}/{:05d}.jpg'.format(img_path, int(fn))
            #print(img_file)
            img = cv2.imread(img_file)
            height, width, _ = img.shape
            imgs.append(img)

        num_rgb_images = len(imgs)


        '''*******  Load Flow  *******'''
        if self.fusion:
            num_input_frames = self.input_frames_flow
            all_frames_ids = []
            first_index = []
            count = 0

            # print(frm_nos, actVidName)
            for fn in frm_nos:
                if numf + 1 <= fn + num_input_frames // 2 + 1:
                    ef = min(numf + 1, fn + num_input_frames // 2 + 1)
                    sf = ef - num_input_frames
                else:
                    sf = max(fn - num_input_frames // 2, 1)
                    ef = sf + num_input_frames
                frames_ids = np.arange(sf, ef)
                c = 0
                for f in frames_ids:
                    if f not in all_frames_ids:
                        all_frames_ids.append(f)
                        c += 1
                if count == 0:
                    first_index.append(0)
                else:
                    first_index.append(c)
                    first_index[count] += first_index[count - 1]
                count += 1

            img_path = '{}{}/{}'.format(self.root, self.input_type_flow, actVidName)
            img = 0
            for fn in all_frames_ids:
                img_file = '{:s}/{:05d}.jpg'.format(img_path, int(fn))
                # print(img_file)
                img = cv2.imread(img_file)
                height, width, _ = img.shape
                imgs.append(img)
            height, width, _ = img.shape

            imgs = np.asarray(imgs)
        #print('imgs shape ', imgs.shape)
        if self.dataset in ['ucf24','jhmdb21']:
            boxes_norm = self.target_transform(gtbxs, width, height, labels, num_mt, self.seq_len)
        else:
            boxes_norm = self.target_transform(gtbxs, 1.0, 1.0, labels, num_mt, self.seq_len)
                                           # normaized gt boxes --->      [xmin ymin xmax ymax label]
        boxes_norm = np.array(boxes_norm)  # converting from list numpy array
        # pdb.set_trace()
        # print(boxes_norm)
        if self.image_set == 'train':
            aug_imgs, aug_bxs, labels = self.transform(imgs, boxes_norm[:, :4], boxes_norm[:, 4], self.seq_len,
                                                           num_mt)  # calling SSDAugmentation
        else:
            aug_imgs, aug_bxs, labels = self.transform(imgs, boxes_norm[:, :4], boxes_norm[:, -1])  # calling BaseTransform

        num_bxs = aug_bxs.shape[0]
        # number of micro tubes after augmentation -- recall after augmentation some micro tubes may be discarded
        # so don't confuse with num_mta and num_mt they are different
        num_mtaa = int(num_bxs / self.seq_len)  # num_mtaa - num micro tube after augmentation


        # aug_imgs is in [seq_len x H x W x C] (0,1,2,3) ---> so converting from RGB (0,1,2) to BGR along 4-th dim
        aug_imgs = aug_imgs[:, :, :, (2, 1, 0)]
        # print('NUm of frame loaded and and required ', aug_imgs.shape[0], ' ', num_input_frames)
        rgb_images = aug_imgs[:num_rgb_images]
        
        if self.input_frames_rgb > 1:
            images = []
            for s in range(self.seq_len):
                sf = first_index[s]
                #print(sf)
                img_stack = rgb_images[sf:sf+num_input_frames,:,:,:]
                img_stack = torch.from_numpy(img_stack).permute(0, 3, 1, 2).contiguous()
                images.append(img_stack.view(-1, img_stack.size(2), img_stack.size(3)))
                #print(images[s].size())
            rgb_images = torch.stack(images, 0)
        else:
            rgb_images = torch.from_numpy(rgb_images).permute(0, 3, 1, 2)
        
        flow_images = torch.zeros(1,1,1)
        if self.fusion:
            flow_images = aug_imgs[num_rgb_images:]
            if self.input_frames_flow > 1:
                images = []
                for s in range(self.seq_len):
                    sf = first_index[s]
                    #print(sf)
                    img_stack = flow_images[sf:sf+num_input_frames,:,:,:]
                    img_stack = torch.from_numpy(img_stack).permute(0, 3, 1, 2).contiguous()
                    images.append(img_stack.view(-1, img_stack.size(2), img_stack.size(3)))
                    #print(images[s].size())
                flow_images = torch.stack(images, 0)
            else:
                flow_images = torch.from_numpy(flow_images).permute(0, 3, 1, 2)

        aug_bxsl = np.hstack((aug_bxs, np.expand_dims(labels, axis=1)))

        return rgb_images, flow_images, aug_bxsl, num_mtaa, index


def detection_collate(batch):
    targets = []
    rgb_imgs = []
    flow_imgs = []
    num_mt = []
    image_ids = []
    # fno = []

    for sample in batch:
        rgb_imgs.append(sample[0])
        flow_imgs.append(sample[1])
        targets.append(torch.FloatTensor(sample[2]))
        num_mt.append(sample[3])
        image_ids.append(sample[4])
    rgb_imgs = torch.stack(rgb_imgs, 0)
    if flow_imgs[0].size(2)>1:
        flow_imgs = torch.stack(flow_imgs, 0)
    return [rgb_imgs, flow_imgs], targets, num_mt, image_ids