import keras
import keras.backend as K
from keras.applications import vgg19
from keras.optimizers import Adam
from keras.layers import Input
from keras.models import Model

from utils import *

# Image reconstruction from layer 'conv4_2'
content_layer = 'block5_conv2'
# Style reconstruction layers
style_layers = ['block1_conv1', 'block2_conv1', 'block3_conv1', 'block4_conv1', 'block5_conv1']

# Content Image Path
content_img_path = 'img/style/starry_night.jpg'
# Style Image Path
style_img_path = 'img/style/starry_night.jpg'
# Number of iterations
num_iterations = 2000
# Content Weight
content_weight = 10.
# Style Weight 0.00000000001 without gram norm
style_weight = 1000.
# Total Varation Weight
tv_weight = 0.
# Image size
img_size = 512
# Style image size
style_size = 512
# Interpolation method
interpolation = 'bicubic'
# Normalize gram matrix
normalize_gram = False
# Scale style loss
scale_style_loss = True
# Init random/content
init = "random"
# Pooling: max or avg
pooling = "avg"
# Learning rate
lr = 10.

# Load images
content_img, new_img_size = load_image(content_img_path, img_size, interpolation)
style_img, new_style_size = load_image(style_img_path, style_size, interpolation)

# Save loaded images, see what we're dealing with
#save_image(content_img, "output/content.jpg", new_img_size)
#save_image(style_img, "output/style.jpg", new_style_size)

# Randomly initialize the generated image
if init == 'random':
    generated_img = K.variable(K.random_normal(content_img.shape, stddev=0.001, seed=1))
    #generated_img = K.variable(K.random_uniform(content_img.shape, -127, 127, seed=1))
elif init == 'content':
    generated_img = K.variable(content_img.copy())

# Load pretrained VGG19 model for content & style targets
# Gatys et al. specify they do not use any fully-connected layers
# Average pooling used to give better gradient flow
model = vgg19.VGG19(include_top=False, pooling=pooling)
#model = vgg19.VGG19(include_top=False, pooling='avg', input_tensor=Input(tensor=generated_img))
model_layers = {layer.name: layer.output for layer in model.layers}

# Get the layers we want from VGG19
content_img_features = [model_layers[content_layer]]
style_img_features = [gram_matrix(model_layers[l], normalize_gram) for l in style_layers]

# Functions for getting the contents of the layers later
get_content = K.function([model.input], content_img_features)
get_style = K.function([model.input], style_img_features)

content_target = get_content([content_img])
style_target = get_style([style_img])

content_target_var = K.variable(content_target[0])
style_target_var = [K.variable(t) for t in style_target]

# Load pretrained VGG19 model with input as generated_img 
model = vgg19.VGG19(include_top=False, pooling=pooling, input_tensor=Input(tensor=generated_img))
model_layers = {layer.name: layer.output for layer in model.layers}
content_img_features = [model_layers[content_layer]]
style_img_features = [gram_matrix(model_layers[l], normalize_gram) for l in style_layers]

# Losses
content_loss = content_loss(content_img_features[0], content_target_var)
style_loss = [style_loss(f,t,new_img_size,scale_style_loss) for f,t in zip(style_img_features, style_target_var)]

# Total variation loss here???
tv_loss = tv_weight * total_variation_loss(generated_img)

total_content_loss = content_loss * content_weight
total_style_loss = K.sum(style_loss)/len(style_loss) * style_weight
total_loss = K.variable(0.) + total_content_loss + total_style_loss + tv_loss

optimizer = Adam(lr=10)#, decay=0.01)
updates = optimizer.get_updates(total_loss, [generated_img])
outputs = [total_loss, total_content_loss, total_style_loss, tv_loss]
step = K.function([], outputs, updates)

losses=[]
for i in range(num_iterations+1):
    print("Iteration %d of %d" % (i, num_iterations))
   
    if i%20 == 0:
        y = K.get_value(generated_img)
        path = "gpuoutput/out_%d.jpg" % i
        img = save_image(y, path, new_img_size)

    res = step([])
    print("Content loss: %g; Style loss: %g; TV loss: %g; Total loss: %g;" % (res[1],res[2],res[3],res[0]))
    
    losses.append((0,res[0]))
    

    #if i > 300:
    #K.set_value(optimizer.lr, max(1, lr-i))
    if i > 500:
        K.set_value(optimizer.lr, 1)
    #print("%f" % K.get_value(optimizer.lr))

with open('gpuoutput/losses.txt', 'w') as f:
    f.write('\n'.join('%d, %d' % (x,y) for x,y in losses))
