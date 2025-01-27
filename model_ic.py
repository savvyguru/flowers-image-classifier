
import numpy as np
import time
from collections import OrderedDict

import torch
from torch import nn
import torch.optim as optim
import torch.nn.functional as F
from torchvision import models

# Define classifier class
class NN_Classifier(nn.Module):
    def __init__(self,output_size):
        ''' Builds a feedforward network with arbitrary hidden layers.
        
            Arguments
            ---------
            input_size: integer, size of the input
            output_size: integer, size of the output layer
            hidden_layers: list of integers, the sizes of the hidden layers
            drop_p: float between 0 and 1, dropout probability
        '''
        super(NN_Classifier, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.conv3 = nn.Conv2d(64, 128, 3, 1)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(774400, 128)
        self.fc2 = nn.Linear(128, output_size)
        
    def forward(self, x):
        #print("Input:", x.shape)
        x = self.conv1(x)
        #print("After conv1:", x.shape)
        x = F.relu(x)
        x = self.conv2(x)
        #print("After conv2:", x.shape)
        x = F.relu(x)
        x = F.max_pool2d(x, 2)
        #print("After max_pool2d:", x.shape)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        #print("After flatten:", x.shape)
        x = self.fc1(x)
        #print("After fc1:", x.shape)
        x = F.relu(x)
        x = self.dropout2(x)
        x = self.fc2(x)
        #print("After fc2:", x.shape)
        output = F.log_softmax(x, dim=1)
        #print("Output:", output.shape)
        return output

# Define validation function 
def validation(model, testloader, criterion, device):
    test_loss = 0
    accuracy = 0
    
    for images, labels in testloader:
        images, labels = images.to(device), labels.to(device)
                
        output = model.forward(images)
        test_loss += criterion(output, labels).item()
        
        ps = torch.exp(output)
        equality = (labels.data == ps.max(dim=1)[1])
        accuracy += equality.type(torch.FloatTensor).mean()

    return test_loss, accuracy

# Define NN function
def make_NN(n_hidden, n_epoch, labelsdict, lr, device, model_name, trainloader, validloader, train_data,testloader):
    class args:
      batch_size = 64 #'input batch size for training (default: 64)')
      test_batch_size = 1000 #'input batch size for testing (default: 1000)')
      epochs = 14 #'number of epochs to train (default: 14)')
      lr = 1.0 #'learning rate (default: 1.0)')
      gamma = 0.7 #'Learning rate step gamma (default: 0.7)')
      no_cuda = False #'disables CUDA training')
      dry_run = False #'quickly check a single pass')
      seed = 1 #'random seed (default: 1)')
      log_interval = 100 #'how many batches to wait before logging training status')
      save_model = False #'For Saving the current Model')
        
    n_epoch = 5
    n_out = len(labelsdict) 
    model = NN_Classifier(n_out).to(device)
    optimizer = optim.Adadelta(model.parameters(), lr=args.lr)
    
#     model_name = "densenet169"
#     # Import pre-trained NN model 
#     model = getattr(models, model_name)(pretrained=True)
    
#     # Freeze parameters that we don't need to re-train 
#     for param in model.parameters():
#         param.requires_grad = False
        
#     # Make classifier
#     n_in = next(model.classifier.modules()).in_features
#     n_out = len(labelsdict) 
#     model.classifier = NN_Classifier(input_size=n_in, output_size=n_out, hidden_layers=n_hidden)
    
#     # Define criterion and optimizer
    criterion = nn.NLLLoss()
#     optimizer = optim.Adam(model.classifier.parameters(), lr = lr)

    start = time.time()

    epochs = n_epoch
    steps = 0 
    running_loss = 0
    print_every = 40
    for e in range(epochs):
        model.train()
        for images, labels in trainloader:
            images, labels = images.to(device), labels.to(device)

            steps += 1

            optimizer.zero_grad()

            output = model.forward(images)
            loss = F.nll_loss(output, labels)
            #loss = criterion(output, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

            if steps % print_every == 0:
                # Eval mode for predictions
                model.eval()

                # Turn off gradients for validation
                with torch.no_grad():
                    test_loss, accuracy = validation(model, validloader, criterion, device)

                print("Epoch: {}/{} - ".format(e+1, epochs),
                      "Training Loss: {:.3f} - ".format(running_loss/print_every),
                      "Validation Loss: {:.3f} - ".format(test_loss/len(validloader)),
                      "Validation Accuracy: {:.3f}".format(accuracy/len(validloader)))

                running_loss = 0

                # Make sure training is back on
                model.train()
    #run on test set
    test_model(model, testloader, device='cuda')
    
    # Add model info 
    model.classifier.n_in = n_in
    model.classifier.n_hidden = n_hidden
    model.classifier.n_out = n_out
    model.classifier.labelsdict = labelsdict
    model.classifier.lr = lr
    model.classifier.optimizer_state_dict = optimizer.state_dict
    model.classifier.model_name = model_name
    model.classifier.class_to_idx = train_data.class_to_idx
    
    print('model:', model_name, '- hidden layers:', n_hidden, '- epochs:', n_epoch, '- lr:', lr)
    print(f"Run time: {(time.time() - start)/60:.3f} min")
    return model

# Define function to save checkpoint
def save_checkpoint(model, path):
    checkpoint = {'c_input': model.classifier.n_in,
                  'c_hidden': model.classifier.n_hidden,
                  'c_out': model.classifier.n_out,
                  'labelsdict': model.classifier.labelsdict,
                  'c_lr': model.classifier.lr,
                  'state_dict': model.state_dict(),
                  'c_state_dict': model.classifier.state_dict(),
                  'opti_state_dict': model.classifier.optimizer_state_dict,
                  'model_name': model.classifier.model_name,
                  'class_to_idx': model.classifier.class_to_idx
                  }
    torch.save(checkpoint, path)
    
# Define function to load model
def load_model(path):
    cp = torch.load(path)
    
    # Import pre-trained NN model 
    model = getattr(models, cp['model_name'])(pretrained=True)
    
    # Freeze parameters that we don't need to re-train 
    for param in model.parameters():
        param.requires_grad = False
    
    # Make classifier
    model.classifier = NN_Classifier(input_size=cp['c_input'], output_size=cp['c_out'], \
                                     hidden_layers=cp['c_hidden'])
    
    # Add model info 
    model.classifier.n_in = cp['c_input']
    model.classifier.n_hidden = cp['c_hidden']
    model.classifier.n_out = cp['c_out']
    model.classifier.labelsdict = cp['labelsdict']
    model.classifier.lr = cp['c_lr']
    model.classifier.optimizer_state_dict = cp['opti_state_dict']
    model.classifier.model_name = cp['model_name']
    model.classifier.class_to_idx = cp['class_to_idx']
    model.load_state_dict(cp['state_dict'])
    
    return model

def test_model(model, testloader, device='cuda'):  
    model.to(device)
    model.eval()
    accuracy = 0
    
    for images, labels in testloader:
        images, labels = images.to(device), labels.to(device)
                
        output = model.forward(images)
        
        ps = torch.exp(output)
        equality = (labels.data == ps.max(dim=1)[1])
        accuracy += equality.type(torch.FloatTensor).mean()
    
    print('Testing Accuracy: {:.3f}'.format(accuracy/len(testloader)))
