#!/usr/bin/env python
# -*- coding: latin-1 -*-


"""
reduce_features: reduce features from the csv files.
"""

import warnings
import sys

import pandas as pd
import numpy as np

from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import TruncatedSVD

from mcr.util import load_config
from mcr.util import KR_AutoEncoder
from mcr.util import KR_LSMTEncoder
from mcr.util import KR_LSTMEmbeddings
from mcr.util import KR_TripletLoss
from mcr.util import my_LinearDiscriminantAnalysis
from mcr.util import build_cache


# Modules configuration
warnings.filterwarnings("ignore")
np.seterr(all='raise')
np.seterr(under="ignore")

memory = build_cache()

__all__ = ['dimension_reduction']

REDUCTION_METHODS = ['PCA', 'LDA', 'RAW', 'TSNE', 'AE', 'LSA', 'LSTM', 'LSTMEMBED', 'TRIPLETLOSS']
MATRIX_METHODS = ['PCA', 'LDA', 'TSNE']
NN_METHODS = ['AE', 'LSTM', 'LSTMEMBED', 'TRIPLETLOSS']

@memory.cache
def dimension_reduction(features, labels, red_method, new_dimension, max_frames=0,
                        save_model=False, standard_scaler=False, output_csv='', 
                        pretrained='', config=None):
    """dimesion_deduction is function that a wraps PCA, LDA, TSNE, LSA, LSTM, 
    LSTMEMBED, and TRIPLETLOSS-embeddings dimension reduction methods

    The input features will be reduced with one of these methods (or raw
    output), it can be removed the std from the features using the std.

    Parameters
    ----------

    features : [list of np.ndarrays]
        list of numpy arrays with numeric floating point elements
    
    labels : [list]
        list with labels/annotations, same length that features list
    
    red_method : [String]
        A string with the the reduction method that will be 
        applied to the features/labels, valid methods are:
        'PCA', 'LDA', 'RAW', 'TSNE', 'AE', 'LSH', 
        'LSTM', 'LSTMEMBED', and 'TRIPLETLOSS'

        From these methods 'PCA', 'LDA', 'RAW', 'TSNE', and 'LSH' are for
        fix length features and  'AE', 'LSTM', 'LSTMEMBED', and 
        'TRIPLETLOSS' can be used with variable length features
    
    max_frames :  [int, optional]
        The maximum number of frames to pass into NN models, if used this 
        argument it should be the maximum number of frames that you will
        expect to have in the future features and it must be higher that
        that from the features
    
    new_dimension : [Integer]
        the new dimension of the features, it should be lower that
        the original feature dimension
    
    standard_scaler :  [Bool]
        Apply the standar scale to all features using scikit-learn StandardScaler
        function

    output_csv : [string, optional]
        The results output csv name, it is only used to set the 
        name of the saved NN model 

    pretrained : [string, optional]
        The file name of the keras NN model that will be used to predict the 
        encodings or embedding, and it is specific for the reduction method
        used to build it.

    config :  [Dict, optional]
        parameters set on the configuration file. 
    
    Returns
    -------
    shrinked_features : [list of np.ndarray] 
        reduced dimension features with the same format that input features 
        with features reduced to the new_dimension size

    labels: [np.ndarray] 
        list of label for the new reduced dimension features 

    """

    if red_method not in REDUCTION_METHODS:
        raise ValueError('red_method {} not supported'.format(red_method))

    if config:
        input_dim = config['features']['nfilt']
    else:
        input_dim = 40  # FIXME: change this hard typed value

    # FEATURES feature reduction
    X_feat = pd.DataFrame(features).values
    n_rows, n_cols = X_feat.shape
    if max_frames != 0:
        if (max_frames - n_cols) < 0:
            raise ValueError, "max_frames should be higher than # features" 
        exten = np.empty([n_rows, max_frames - n_cols])
        exten[:] = np.nan 
        X_feat = np.append(X_feat, exten, axis=1)

    labels = np.array(labels)
    is_matrix = False if np.object == X_feat.dtype else True

    if not is_matrix and (red_method in MATRIX_METHODS):
        print('all features should have the same dimension')
        sys.exit()

    if standard_scaler and is_matrix and np.isnan(X_feat).all():
        X_feat = StandardScaler().fit_transform(X_feat)

    if red_method == 'PCA' and is_matrix:
        pca = PCA(n_components=new_dimension)
        shrinked_features = pca.fit_transform(X_feat)

    elif red_method == 'LDA' and is_matrix:
        lda = my_LinearDiscriminantAnalysis(n_components=new_dimension)
        lda.fit(X_feat, labels)
        shrinked_features = lda.transform(X_feat)

    elif red_method == 'LSA' and is_matrix:
        lsa = TruncatedSVD(n_components=new_dimension, n_iter=50,
                           algorithm='arpack', random_state=42)
        shrinked_features = lsa.fit_transform(X_feat)

    elif red_method == 'TSNE' and is_matrix:
        tsne = TSNE(n_components=new_dimension, method='exact',
                    random_state=42)
        shrinked_features = tsne.fit_transform(X_feat)

    elif red_method == 'LSTM' and is_matrix:
        kr_lstm = KR_LSMTEncoder(X_feat, labels, input_dim)
        
        if pretrained:
            kr_lstm.load_encoder(pretrained)
        else:
            kr_lstm.fit(n_dimensions=new_dimension)
        
        if save_model:
            kr_lstm.save_encoder('{}.hdf5'.format(output_csv))
        
        shrinked_features = kr_lstm.reduce()
    
    elif red_method == 'LSTMEMBED' and is_matrix:
        kr_lstmemb = KR_LSTMEmbeddings(X_feat, labels)
        
        if pretrained:
            kr_lstmemb.load_encoder(pretrained)
        else:
            kr_lstmemb.fit(n_dimensions=new_dimension)
        
        if save_model:
            kr_lstmemb.save_encoder('{}.hdf5'.format(output_csv))
        
        shrinked_features = kr_lstmemb.reduce()

    elif red_method == 'AE' and is_matrix:
        kr_ae = KR_AutoEncoder(X_feat, labels)

        if pretrained:
            kr_ae.load_encoder(pretrained)
        else:
            kr_ae.fit(n_dimensions=new_dimension)

        if save_model:
            kr_ae.save_encoder('{}.hdf5'.format(output_csv))
        
        shrinked_features = kr_ae.reduce()

    elif red_method == 'TRIPLETLOSS' and is_matrix:
        kr_tl = KR_TripletLoss(X_feat, labels)

        if pretrained:
            kr_tl.load_encoder(pretrained)
        else:
            kr_tl.fit(n_dimensions=new_dimension)

        if save_model:
            kr_tl.save_encoder('{}.hdf5'.format(output_csv))

        shrinked_features = kr_tl.reduce()
    
    else:  # default = raw
        shrinked_features = X_feat

    # I return a list of np.ndarrays, unfolding the list
    shrinked_features = [x for x in shrinked_features]

    return shrinked_features, labels


def main():
    import argparse

    parser = argparse.ArgumentParser(prog=sys.argv[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='prepare the csv or abx files to compute ABX score')

    parser.add_argument('features_source', 
            help='csv file with the features')

    parser.add_argument('algorithm_config', 
            help='algorithm configuration file for the feature extraction')

    parser.add_argument('-o', '--out_csv', required=True, 
            help='output features and labels in csv format')

    parser.add_argument('-m', '--max_frames', required=False, default=0, 
            help='max number of frames when training the RNN')

    parser.add_argument('--standard_scaler', action='store_true', default=False, required=False,
            help='scale the features')

    parser.add_argument('--save_model', default=False, action='store_true', required=False,
            help='save keras trained model')

    parser.add_argument('--pretrained', required=False,
            help='load pretrained NN model that will be use to do the dimension reduction')

    help_reduction = """use dimension reduction, valid methods are raw, pca, 
    lda, lsa, tsne, ae [autoencoder], lstm, lstmembed and tripletloss, 
    these two last methods gives embeddings"""

    parser.add_argument('-r', '--reduction', help=help_reduction)

    args = parser.parse_args()
    data_file = args.features_source
    reduction_type = args.reduction
    config_file = args.algorithm_config
    output_csv = args.out_csv
    standard_scaler = args.standard_scaler
    save_model = args.save_model
    pretrained = args.pretrained
    max_frames = int(args.max_frames)

    # CONFIGURATION
    config = load_config(config_file)

    # check if the selected reduction dimension algorithm is supported
    if reduction_type:
        red_method = reduction_type
        red_method = red_method.upper()
        if red_method not in REDUCTION_METHODS:
            print('--reduction valid algorithms: {} -- "{}" given'.format('  '.join(REDUCTION_METHODS),
                  red_method))
            sys.exit()

        try:
            # the config file should have also declared the selected algorithm 
            new_dimension = config['dimension_reduction'][red_method]
        except:
            print('missing section dimension_reduction in config file [{}]'.format(red_method))
            sys.exit()

    else: # default method is None that will trigger the raw dimension reduction
       red_method = None

    if pretrained and red_method not in NN_METHODS:
        print('valid pretrained models are: {}, given {}'.format(NN_METHODS, red_method))
        sys.exit()

    # Read features file, the format of the file is simple, it is a csv without
    # header and with the following data-fields:
    #
    # label1,f11,f12,f13, .. f1J-1,f1J 
    # ....
    # labelN,fN1,fN2,fN3, .. fMJ-1,fMJ
    #
    # where N ar the samples/calls and J number of features,
    # labels can be any type of printable objects (int, float, str)
    # and features are floats
    # 

    # I read this csv by hand (not numpy or pandas) as it 
    # can contain a variable number of features
    labels_from_csv = []
    features_from_csv = []
    with open(data_file, 'r') as dfile:
        for line in dfile.readlines():
            row = line.strip().split(',')
            labels_from_csv.append(row[0])  # label/call in the first column
            features_from_csv.append([float(x) for x in row[1:]])

    # Apply feature reduction
    features, labels = dimension_reduction(features_from_csv, labels_from_csv,
                                           red_method, new_dimension, max_frames,
                                           save_model, standard_scaler, output_csv, 
                                           pretrained, config)
    
    # write out the reduced dimension into a new file
    with open(output_csv, 'w') as emb_csv:
        for label, feats in zip(labels, features):
            t = '{},'.format(label) + ','.join(['{}'.format(x)
                                                for x in feats]) + '\n'
            emb_csv.write(t)


if __name__ == '__main__':
    main()
