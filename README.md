# Docker Registry Trace Player

The Docker registry trace player is used to replay anonimized production level traces for a registry, available in the traces directory.
The traces are from the IBM docker registry, separated by availability zones.
The trace player can send traces to an actual registry or be used to simulate different caching or prefetching. The registry must be confiugred as a test registry in the current version, however.

The trace player has two applications: the master and the client. The master is reponsible for reading a trace, generating layers, and distributing the layer requests amoung client applications to forward to a registry. The client application is only needed for the run mode.

The trace player has 3 modes:

* warmup
* run
* simulate

The warmup mode connects to a registry and pushes all the layers in the traces specified by the configuration file. Layers are generated as a string of 0's equal to the size of the request reported in the trace. Because the traces are anonimized, manifests are are treated as layers for the warmup and run modes. During warmup, layers will be pushed to the first registry in the configuration file.

The Run mode replays the anonymized traces to the registry or registries specified in the configuration file. One or more clients need to be up before the master node is started.

The simulate mode takes a python file from the configuration file and attempts to call an init function from it. If arguments are specified in the configuration file, then init will be called with two arguments: a sorted list of the requests, and a dictionary of the arguments. If arguments are not specified, then init will be called with just the list of requests.

# Usage

To Run the master:

python master.py -c <command> -i <config.yaml>

Possible commands: warmup, run, and simulate

To run client:

python client.py -i 0.0.0.0 -p <port number>

## Configuration file Options

The configuration should be a yaml file, refer to config-example.yaml as an example. The following are all the supported options for the configuration file. Options not needed for a given mode will be ignored.

###Options:

#### Cient_info

* required for run mode

client_info options:

* client_list: list of hostname:port for all client nodes. Required option
* port: int, the master port the clients will connect to to forward their results.
* threads: int, Specifies how many processes a single client should spawn to forward requests. The number of possible concurrent connections is limited by the number of threads per client times the number of clients
* wait: boolean, if true, the client threads will wait the relative time between requests as recorded in the traces. If false or absent, the clients will send requests as fast as possible.
* route: optional boolean which instructs the master to route requests to clients based on the remote address of the traces rather than round robin routing.

#### verbose
* Optional Booblean, if true prints more information to standard out

#### trace
* Required for all modes

trace options:

* location, optional path to the anonymized traces, current directory assumed if absent. Absolute path should be used.
* traces, mandatory list of trace files to be read as input
* limit, optional structure to specify how to limit the number of requests
..* type: string that can be either "seconds" or "requests" 
..* amount: specifies the limit of the specified type. For example, if type is seconds and amount is 100, only the first 100 seconds of requests will be used
* output: optional filename of where to store output trace of run mode. Default is output.json

### registry

* list of registries to send requests to in warmup and run mode. Only first entry is used in warmup mode, however

### warmup

* required for run and warmup modes

Options:

* output: required filename, is populated by warmup and needed by run for mapping the trace uri to a blob
* threads: optional int, specifies how many threads should be used to send requests to registry in warmup mode
* random: optional boolean, instructs the master to create random files for layers rather than creating files of 0's

### simulate

* Required for simulate mode

Options:

* name: required string, should be the name of the python file containing the simulation. File should contain an init(requests) or init(requests, args) function to start the simulation
* args: optional dictionary that can contain any arguments the simulation needs

### Example


client_info:

    client_list:
        - localhost:8081
        - localhost:8082
    port: 8080
    threads: 100
    wait: true

verbose: true

trace:

    location: /data/data_centers/dal09
    traces:
        - prod-dal09-logstash-2017.08.01-0.json
    limit:
        type: requests
        amount: 20

    output: results.json

registry:

    - localhost:5000

warmup:

    output: interm.json

    threads: 100

simulate:

    name: cache.py
    args:
        cache_size: 8


# Instalation

sudo apt-get install python-pip

sudo pip install python-dxf

sudo pip install requests

sudo pip install bottle

sudo pip install pyyaml

sudo pip install hash_ring

# Data format for simulation
* sorted by delay (timestamp of request)

[

    {
        'delay': timestamp (int),
        'uri': 'v2/user/repo/<blobs or manifests>/layer',
        'size', size (int),
        'method': <'GET' or 'PUT'>,
        'duration': duration (int),
        'client': remote address (string)
    },
]

# Support Channel

Michael Littley: milit93@vt.edu
Ali Anwar: ali@vt.edu

Support is also available through the github repository
