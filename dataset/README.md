# Dataset Presentation

PicoPix project aim to colorize images. So there are different datasets that can be used to train the model. In our case, we selected [MSCOCO](https://cocodataset.org/#download). This dataset is already splited into 3 sets that are ttrain, validation and test.  

In our case, we will use only the *validation set* in order to train and test our model due the quantity of data and computational ressources.


If you want to use all dataset as provided by Microsoft, run the following commands  to download them.

```bash
wget http://images.cocodataset.org/zips/train2017.zip
wget http://images.cocodataset.org/zips/val2017.zip
wget http://images.cocodataset.org/zips/test2017.zip

unzip train2017.zip
unzip vald2017.zip
unzip test2017.zip
```