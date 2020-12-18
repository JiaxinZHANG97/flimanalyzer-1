#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 16 14:18:30 2020

@author: khs3z
"""

import logging
import wx
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn import metrics
from analysis.absanalyzer import AbstractAnalyzer


class RandomForest(AbstractAnalyzer):
    
    def __init__(self, data, categories, features, classifier=None, importancehisto=True, n_estimators=100, test_size=0.3):
        AbstractAnalyzer.__init__(self, data, categories, features)
        self.name = "Random Forest"
        self.params = {
            'importancehisto':importancehisto,
            'n_estimators': n_estimators,
            'test_size': test_size,
            'classifier': classifier}
    
    def __repr__(self):
        return f"{'name': {self.name}}"
    
    def __str__(self):
        return self.name
    
    def get_required_categories(self):
        return ['any']
    
    def get_required_features(self):
        return ['any']
    
    def run_configuration_dialog(self, parent):
        category_cols = self.data.select_dtypes(['category']).columns.values
        dlg = wx.SingleChoiceDialog(parent, 'Choose feature to be used as classifier', 'Random Forest Classifier', category_cols)
        if dlg.ShowModal() == wx.ID_OK:
            parameters = {'classifier': dlg.GetStringSelection()}
            self.configure(**parameters)
            return parameters
        return  # implicit None
    
    def execute(self):
        results = {}
        data = self.data.dropna(how='any', axis=0)
        data_features = [f for f in self.features if f not in self.categories]
        X=data[data_features]  # Features
        y=data[self.params['classifier']]  # Labels
        # Split dataset into training set and test set
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=self.params['test_size'])
        #Create a Gaussian Classifier
        clf=RandomForestClassifier(n_estimators=self.params['n_estimators'])
        #Train the model using the training sets y_pred=clf.predict(X_test)
        clf.fit(X_train,y_train)

        y_pred=clf.predict(X_test)
        
        accuracy = metrics.accuracy_score(y_test, y_pred)
        importance_df = pd.DataFrame({'Feature': self.features, 'Importance Score':clf.feature_importances_})
        importance_df.sort_values(by='Importance Score', ascending=False, inplace=True)
        if self.params['importancehisto']:
            importance_plot = importance_df.set_index('Feature').plot.bar()
            fig = importance_plot.get_figure()
            ax = fig.get_axes()[0]
            ax.text(0.95, 0.80, f'accuracy={accuracy:.3f}', 
                        horizontalalignment='right',
                        verticalalignment='center',
                        transform = ax.transAxes)
            results['Importance Score Plot'] = (fig,ax)
        # results['Accuracy'] = accuracy
        results['Importance Score Data'] = importance_df
        return results
            