import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import os


class RNN:
    def __init__(self, batchsize, length):
        self.batchsize = batchsize
        self.outputshape = length

    def _input_add_state(self, input, state, active_fn=tf.nn.tanh, name=None):
        inputshape = input.get_shape().as_list()
        with tf.variable_scope(name):
            u = tf.get_variable(name='U', initializer=tf.random_uniform((inputshape[-1], self.outputshape)))
            w = tf.get_variable(name='W', initializer=tf.random_uniform((self.outputshape, self.outputshape)))
            b = tf.get_variable(name='B', initializer=tf.random_uniform((inputshape[0], self.outputshape)))
            return active_fn(tf.matmul(input, w) + tf.matmul(state, u) + b)


class LSTM(RNN):
    def __init__(self, batchsize, length):
        #super(self).__init__(batchsize, length)
        self.batchsize = batchsize
        self.outputshape = length
        self.state = tf.Variable(tf.zeros((self.batchsize, self.outputshape)),trainable=False)
        self.candidate = tf.Variable(tf.random_uniform((self.batchsize, self.outputshape)),trainable=False)

    def build(self, inputs, reuse=False):
        with tf.variable_scope('LSTM', reuse=reuse):
            forget = self._input_add_state(inputs, self.state, name='forget')
            inputgate = self._input_add_state(inputs, self.state, name='inputgate')
            output = self._input_add_state(inputs, self.state, name='output')
            self.candidate = tf.multiply(forget, self.candidate) + tf.multiply(inputgate,
                                                                               self._input_add_state(inputs, self.state,
                                                                                                     tf.nn.tanh,
                                                                                                     #tf.nn.sigmoid,
                         #tf.nn.relu,
                                                                                                     name='candi'))
            self.state = tf.multiply(output, self.candidate)
        return output


class GRU:
    """Implementation of a Gated Recurrent Unit (GRU) as described in [1].
    [1] Chung, J., Gulcehre, C., Cho, K., & Bengio, Y. (2014). Empirical evaluation of gated recurrent neural networks on sequence modeling. arXiv preprint arXiv:1412.3555.
    Arguments
    ---------
    input_dimensions: int
        The size of the input vectors (x_t).
    hidden_size: int
        The size of the hidden layer vectors (h_t).
    dtype: obj
        The datatype used for the variables and constants (optional).
    """

    def __init__(self, input_dimensions, hidden_size, dtype=tf.float64):
        self.input_dimensions = input_dimensions
        self.hidden_size = hidden_size

        # Weights for input vectors of shape (input_dimensions, hidden_size)
        self.Wr = tf.Variable(
            tf.truncated_normal(dtype=dtype, shape=(self.input_dimensions, self.hidden_size), mean=0, stddev=0.01),
            name='Wr')
        self.Wz = tf.Variable(
            tf.truncated_normal(dtype=dtype, shape=(self.input_dimensions, self.hidden_size), mean=0, stddev=0.01),
            name='Wz')
        self.Wh = tf.Variable(
            tf.truncated_normal(dtype=dtype, shape=(self.input_dimensions, self.hidden_size), mean=0, stddev=0.01),
            name='Wh')

        # Weights for hidden vectors of shape (hidden_size, hidden_size)
        self.Ur = tf.Variable(
            tf.truncated_normal(dtype=dtype, shape=(self.hidden_size, self.hidden_size), mean=0, stddev=0.01),
            name='Ur')
        self.Uz = tf.Variable(
            tf.truncated_normal(dtype=dtype, shape=(self.hidden_size, self.hidden_size), mean=0, stddev=0.01),
            name='Uz')
        self.Uh = tf.Variable(
            tf.truncated_normal(dtype=dtype, shape=(self.hidden_size, self.hidden_size), mean=0, stddev=0.01),
            name='Uh')

        # Biases for hidden vectors of shape (hidden_size,)
        self.br = tf.Variable(tf.truncated_normal(dtype=dtype, shape=(self.hidden_size,), mean=0, stddev=0.01),
                              name='br')
        self.bz = tf.Variable(tf.truncated_normal(dtype=dtype, shape=(self.hidden_size,), mean=0, stddev=0.01),
                              name='bz')
        self.bh = tf.Variable(tf.truncated_normal(dtype=dtype, shape=(self.hidden_size,), mean=0, stddev=0.01),
                              name='bh')

        # Define the input layer placeholder
        self.input_layer = tf.placeholder(dtype=tf.float64, shape=(None, None, input_dimensions), name='input')

        # Put the time-dimension upfront for the scan operator
        self.x_t = tf.transpose(self.input_layer, [1, 0, 2], name='x_t')

        # A little hack (to obtain the same shape as the input matrix) to define the initial hidden state h_0
        self.h_0 = tf.matmul(self.x_t[0, :, :], tf.zeros(dtype=tf.float64, shape=(input_dimensions, hidden_size)),
                             name='h_0')

        # Perform the scan operator
        self.h_t_transposed = tf.scan(self.forward_pass, self.x_t, initializer=self.h_0, name='h_t_transposed')
        # Transpose the result back
        self.h_t = tf.transpose(self.h_t_transposed, [1, 0, 2], name='h_t')

    def forward_pass(self, h_tm1, x_t):
        """Perform a forward pass.
        Arguments
        ---------
        h_tm1: np.matrix
            The hidden state at the previous timestep (h_{t-1}).
        x_t: np.matrix
            The input vector.
        """
        # Definitions of z_t and r_t
        z_t = tf.sigmoid(tf.matmul(x_t, self.Wz) + tf.matmul(h_tm1, self.Uz) + self.bz)
        r_t = tf.sigmoid(tf.matmul(x_t, self.Wr) + tf.matmul(h_tm1, self.Ur) + self.br)
        # Definition of h~_t
        h_proposal = tf.tanh(tf.matmul(x_t, self.Wh) + tf.matmul(tf.multiply(r_t, h_tm1), self.Uh) + self.bh)
        # Compute the next hidden state
        h_t = tf.multiply(1 - z_t, h_tm1) + tf.multiply(z_t, h_proposal)
        return h_t


class Generator:
    def __init__(self, start, time_steps):
        self.start = start
        self.steps = time_steps

    def next(self):
        while True:
            var = np.arange(self.start, self.start + 10 * self.steps, self.steps)
            inputs = np.cos(var + 20) + np.cos(var * 0.1 + 2)
            output = np.sin(inputs)
            self.start += 10 * self.steps
            yield inputs.astype(np.float32), output.astype(np.float32), var.astype(np.float32)

def sigmoid(x):
    # TODO: Implement sigmoid function
    return 1/(1 + np.exp(-x))

def argsigmoid(x):
    return np.log(x)-np.log(1-np.clip(x,0.0001,0.9999999))

def MaxMinNormalization(x,Max,Min):
	x = (x - Min) / (Max - Min);
	return x;

def argnorm(x,Max,Min):
    x = (Max-Min)*x+Min
    return x;

class MyGenerator:
    def __init__(self, start, time_steps,filename):
        self.start = start
        self.steps = time_steps
        self.filename = filename
        self.datas = []
        for line in open(filename):
            line = line.strip()
            cols = line.split(" ")
            for data in cols:
                self.datas.append(float(data))
        self.max = np.max( np.array(self.datas))
        self.min = np.min( np.array(self.datas))
    
    def getMaxmin(self):
        return self.max,self.min
    
    def next(self):
        while True:
            #inputs = sigmoid( np.array( self.datas[self.start:self.start+self.steps]) )
            inputs = MaxMinNormalization( np.array( self.datas[self.start:self.start+self.steps]),self.max, self.min)
            #outputs = sigmoid( np.array( self.datas[self.start+self.steps:self.start+2*self.steps]) )
            #outputs = sigmoid( np.array( self.datas[self.start+self.steps:self.start+self.steps+1]) )
            #outputs = sigmoid( np.array( self.datas[self.start+1:self.start+self.steps+1]) )
            outputs = MaxMinNormalization( np.array( self.datas[self.start+1:self.start+self.steps+1]),self.max,self.min)
            #outputs = np.sin(inputs)
     
        #    print "filename=",self.filename 
        #    print "start=",self.start
        #    print "steps=",self.steps
            print "max=",self.max
            print "min=",self.min
            print "input=",inputs
            print "output=",outputs
            self.start +=  2*self.steps
            yield inputs.astype(np.float32), outputs.astype(np.float32)

def test():
    os.environ['CUDA_VISIBLE_DEVICES'] = '1'
    batchsize = 10
    #seq size, or can be named outputshape size
    seq_size = 7
 
    #prepare data
    #generate 3*float data,* 3
    gen1 = MyGenerator(0, seq_size, "data.lstm.trim.txt")
    print gen1
    max,min = gen1.getMaxmin()
    #generate 3*float data,* 3
    gen2 = MyGenerator(0, seq_size, "data.lstm.trim.txt")
    #Here parameter2 should be consistent with gen input size
    data = tf.data.Dataset.from_generator(gen1.next, (tf.float32,tf.float32) )
    #Here parameter2 should be consistent with gen input size
    test_data = tf.data.Dataset.from_generator(gen2.next, (tf.float32,tf.float32))
    data = data.batch(batchsize)
    train_data = data.make_one_shot_iterator()
    test_data = test_data.batch(batchsize).make_one_shot_iterator()
    print train_data
    print test_data
   
    #Here should match get_next yield data, for example, yield 3 element, return 3 element
    #Here input feature and label 
    tinputs, tgroundtruth = train_data.get_next()
    print tinputs
    test_input, test_gt = test_data.get_next()
    print test_input
    #Here reshape tinputs to shape batchsize*seq_size , so sizeof(tinputs)=batchsize*seq_size
    #Assert sizeof(tinputs)==batchsize*seq_size
    tinputs, test_input = tf.reshape(tinputs, (batchsize, seq_size)), tf.reshape(test_input, (batchsize, seq_size)) 
    print tinputs
    print tinputs[0]
    print tf.rank(tinputs) 
    print tinputs[0][0]  
    print tf.rank(tinputs[0])   
    
    gpu_options = tf.GPUOptions(allow_growth=True)
    #with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, allow_soft_placement=True)) as sess:
    #   sess.run(tinputs)
    
    #prepare model
    #model defination
    # input size = seq_size
    net = LSTM(batchsize, seq_size)
    output = net.build(tinputs)
    #output size = 1, not seq_size
    net = LSTM(batchsize, seq_size)
    test_output = net.build(test_input, True) 
    #loss function
    #loss = tf.reduce_mean(tf.abs(output - tgroundtruth))
    #self define loss function
    loss = tf.reduce_mean(tf.where( 
       tf.greater(output,tgroundtruth), (output-tgroundtruth), (tgroundtruth-output)*2
       ))
    #loss = tf.reduce_mean(tf.square(output - tgroundtruth))
    #optimization function
    train_opt = tf.train.RMSPropOptimizer(1e-2).minimize(loss)
    gpu_options = tf.GPUOptions(allow_growth=True)
    
    #start to train
    with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, allow_soft_placement=True)) as sess:
        sess.run(tf.global_variables_initializer())
        fig = plt.figure()
        for epoch in range(1400):
            print "epoch = ",epoch
            print "--------------"
            sess.run(train_opt)
            if not epoch % 20:
                src, gt, pred, l, state = sess.run([test_input, test_gt, test_output, loss, output])
                #src = sess.run(test_var)
                #gt = sess.run(test_gt)
                #tf.Print(test_input, [test_input], message="test_input")
                #pred = sess.run(test_output)
                #l = sess.run(loss)
                print(epoch, '|', l)
                print("input")
                print(src.ravel())
                #print(argsigmoid(src.ravel()) )
                print(argnorm(src.ravel(),max,min) )
                print("label")
                print(gt.ravel())
                #print(argsigmoid(gt.ravel()) )
                print(argnorm(gt.ravel(),max,min) )
                print("pred")
                print(pred.ravel())
                print(argnorm( pred.ravel(),max,min) )
                #conv_loss = sess.run(tf.reduce_mean(tf.abs( argsigmoid(gt.ravel())-argsigmoid(pred.ravel()))) )
                conv_loss = sess.run(tf.reduce_mean(tf.abs( argnorm(gt.ravel(),max,min)-argnorm(pred.ravel(),max,min))) )
                print(conv_loss.ravel())
                print ("stat")
                print("=====")
                print(state.ravel())
                print("=====")
'''
               # update plotting
                plt.cla()
                fig.set_size_inches(7, 4)
                plt.title(str(epoch))
                plt.plot(src.ravel(), gt.ravel(), label='ground truth')
                plt.plot(src.ravel(), pred.ravel(), label='predicted')
                plt.ylim((-10, 10))
                plt.xlim((src.ravel()[0], src.ravel()[-1]))
                plt.legend(fontsize=15)
                plt.draw()
                plt.pause(0.1)
                # plt.savefig(r'G:\temp\blog\gif\\' + str(epoch) + '.png', dpi=100)
'''

if __name__ == '__main__':
    test()
