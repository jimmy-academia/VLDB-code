#!/bin/bash

datadir="data"

if [ ! -d "$datadir" ]; then
    mkdir -p "$datadir"
    echo "created directory to store dataset: $datadir"
fi

traitdatadir="data/trait_data"
buyerdatadir="data/buyer_data"

if [ ! -d "$traitdatadir" ]; then
    echo "downloading nft trait data..."
    wget https://github.com/jimmy-academia/ICDE24/releases/download/nftdata/trait_data.zip
    unzip trait_data.zip
    rm trait_data.zip
    mv trait_data data/
else
    echo "trait data already downloaded and unzipped."
fi


if [ ! -d "$buyerdatadir" ]; then
    echo "downloading nft buyer data..."
    wget https://github.com/jimmy-academia/ICDE24/releases/download/nftdata/buyer_data.zip
    unzip buyer_data.zip
    rm buyer_data.zip
    mv buyer_data data/
else
    echo "buyer data already downloaded and unzipped."
fi


