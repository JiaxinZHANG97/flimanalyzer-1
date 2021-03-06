#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time  : 12/1/20 7:04 PM
# @Author: Jiaxin_Zhang

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.optim as optim
import torch.utils.data
from sklearn import preprocessing
from sklearn.impute import SimpleImputer
from autoencoder2 import AE
from dataset import datasets


class AEtraining(object):
    def __init__(self, data, FLIM_variables, epoches, learning_rate, weight_decay, batch_size):
        self.data = data
        self.variables = FLIM_variables
        self.epoches = epoches
        self.lr = learning_rate
        self.wd = weight_decay
        self.bs = batch_size

    def create_datasets(self):
        self.data.rename(columns={'FLIRR':'FLIRR (NAD(P)H a2[%]/FAD a1[%])'}, inplace=True)

        ind = list(self.data.columns)
        ind_cell = ind.index('Cell')
        ind_fov = ind.index('FOV')
        ind_tre = ind.index('Treatment')
        self.len_info = ind_tre+1

        g = self.data.loc[:,self.variables]
        info = self.data.iloc[:, 0:self.len_info]
        data_set = pd.concat([info, g],axis=1)
        self.data_copy = data_set.copy()

        FOV = self.data_copy.loc[:,'FOV']
        FOV_u = np.unique(FOV)
        timepoint = self.data_copy.loc[:,'Treatment']
        tp_u = np.unique(timepoint)
        print('FOV: ', FOV_u)
        print('Timepoint: ', tp_u)

        f = self.data.loc[:,'FLIRR (NAD(P)H a2[%]/FAD a1[%])']
        self.data_set_f = pd.concat([data_set,f],axis=1)
        data_set = np.array(data_set)
        data_set_f_np = np.array(self.data_set_f)

        # Split data into training and test sets
        training_set = np.zeros([1, data_set.shape[1]])
        val_set = np.zeros([1, data_set.shape[1]])

        for t in range(len(tp_u)):
            # print(tp_u[t])
            mask_time = (timepoint == tp_u[t])
            data_t = data_set_f_np[mask_time]

            for i in range(len(FOV_u)):
                data_len = data_t[data_t[:, ind_fov] == FOV_u[i]]  # 4 or 3
                cell = data_len[:, ind_cell]
                n_c = np.unique(cell)
                k = int(np.around(0.7 * len(n_c)))
                # print(n_c)

                mask_train = (cell <= k)
                mask_val = (cell > k)
                data_t_mask = data_len[mask_train][:, :-1]
                data_v_mask = data_len[mask_val][:, :-1]
                training_set = np.append(training_set, data_t_mask, axis=0)
                val_set = np.append(val_set, data_v_mask, axis=0)
                # print('training', training_set.shape)
                # print('val', val_set.shape)

        training_set = training_set[1:, self.len_info:]
        val_set = val_set[1:, self.len_info:]

        my_imputer = SimpleImputer(strategy="constant", fill_value=0)
        min_max_scaler = preprocessing.MinMaxScaler()

        training_set_1 = training_set.astype(float)
        training_set_1 = min_max_scaler.fit_transform(training_set_1)  # Normalization
        training_set = my_imputer.fit_transform(training_set_1)
        self.training_set = torch.FloatTensor(training_set)
        self.param = self.training_set.size(1)
        print('Training set shape:', self.training_set.size())

        val_set_1 = val_set.astype(float)
        val_set_1 = min_max_scaler.fit_transform(val_set_1)  # Normalization
        val_set = my_imputer.fit_transform(val_set_1)
        self.val_set = torch.FloatTensor(val_set)
        print('Val set shape:', self.val_set.size())

    def load_data(self):
        col = self.data_copy.columns.values[self.len_info:]
        t_set = np.array(self.training_set)
        v_set = np.array(self.val_set)
        training_frame = pd.DataFrame(t_set, index=None, columns=col)
        val_frame = pd.DataFrame(v_set, index=None, columns=col)

        train_dataset = datasets(training_frame)
        val_dataset = datasets(val_frame)
        self.train_loader = torch.utils.data.DataLoader(dataset=train_dataset,
                                                        batch_size=self.bs,
                                                        shuffle=True)
        self.val_loader = torch.utils.data.DataLoader(dataset=val_dataset,
                                                    batch_size=self.bs,
                                                    shuffle=True)
        return self.train_loader

    def training(self):
        ae = AE(self.param)
        ae = ae.cuda()
        criterion = nn.MSELoss().cuda()
        optimizer = optim.RMSprop(ae.parameters(), self.lr, self.wd)

        loss_train = []
        loss_val = []

        # Train the autoencoder
        for epoch in range(1, self.epoches + 1):
            cum_loss = 0

            for (i, inputs) in enumerate(self.train_loader):
                inputs = inputs.cuda()
                encoder_out, decoder_out = ae(inputs)

                loss = criterion(decoder_out, inputs)
                cum_loss += loss.data.item()

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                if (i + 1) % 100 == 0:
                    print('Train-epoch %d. Iteration %05d, Avg-Loss: %.4f' % (epoch, i + 1, cum_loss / (i + 1)))

            loss_train.append(cum_loss / (i + 1))
            cum_loss = 0

            for (i, inputs) in enumerate(self.val_loader):
                inputs = inputs.cuda()
                encoder_out, decoder_out = ae(inputs)

                loss = criterion(decoder_out, inputs)
                cum_loss += loss.data.item()

            print('Validation-epoch %d. Iteration %05d, Avg-Loss: %.4f' % (epoch, i + 1, cum_loss / (i + 1)))

            loss_val.append(cum_loss / (i + 1))

        print("\n")
        print("loss_TrainingSet:",loss_train[-1])
        print("loss_TestSet:",loss_val[-1])
        print("\nTraining complete!\n")
        # torch.save(ae, self.data + '_autoencoder.pkl')

        plt.figure(figsize=(10, 4))
        plt.plot(loss_train, 'b-', label='train-loss')
        plt.plot(loss_val, 'r-', label='val-loss')
        plt.grid('on')
        plt.ylabel('loss')
        plt.xlabel('epoch')
        plt.legend(['training', 'testing'], loc='upper right')
        plt.show()
        # plt.savefig(self.data + '_AE_loss.png')
