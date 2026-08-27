# Bat-Q: A Streamlit App for Network Analysis with Batfish

Bat-Q is a [Streamlit](https://streamlit.io/) app that lets you run various network analysis queries using [Batfish](https://www.batfish.org/), an open source network configuration analysis tool. You can upload your network configuration files as snapshots and analyze different scenarios or states. You can also select from a wide range of Batfish [questions](https://www.google.com/search?q=https://pybatfish.readthedocs.io/en/latest/index.html) to get insights into your network's behavior and security. Bat-Q displays the answers in tables and diagrams for easy interpretation.

Bat-Q is designed to be simple, interactive, and flexible. You can use it for quick network configuration checks or for network troubleshooting and optimization tasks. Bat-Q is not a replacement for [pyBatfish](https://github.com/batfish/pybatfish), the Python API for Batfish, but rather a complementary tool that can help you get started with network analysis using Batfish.

To learn more about Bat-Q and how to use it, please watch these [YouTube tutorials](https://www.google.com/search?q=https://www.youtube.com/playlist%3Flist%3DPLcWqK41-5YzIpiT223KToro0iaTww-58t) (work in progress).

## Release Notes - Version v0.2

Version v0.2 introduces key architectural updates, interactive visualization, improved snapshot management, and enhanced user feedback:

- Imporved navigation
- Interactive topology visualization
- Enhanced snapshot management
- DataFrame & schema optimization
- Report and spreadsheet generation

## Requirements

To use Bat-Q, you will need:

- A Batfish server capable of running Docker: See the recommended [requirements for Batfish](https://batfish.readthedocs.io/en/latest/system_req.html).
- A host to run the Bat-Q app.

Note that for training purposes with small networks, you can use one computer to run both Batfish and Bat-Q (a reasonable laptop will work).

## Installation

To use the app, follow these steps (assuming Ubuntu Linux, but Windows also works):

### Batfish server

1. Install Docker: There are multiple methods, but I recommend using [the apt repository method](https://www.google.com/search?q=https://docs.docker.com/engine/install/ubuntu/%23install-using-the-repository).
2. To use Docker as a non-privileged user, add the user to the Docker group:
    ```bash
    $ sudo usermod -aG docker $USER
    ```
3. Install Batfish and run the Batfish services:
    ```bash
    $ docker pull batfish/allinone
    $ docker run --name batfish -d --restart unless-stopped -v batfish-data:/data -p 9997:9997 -p 9996:9996 batfish/allinone
    ```

    or, to run on local host:

    ```bash
    $ docker run --name batfish -d --net host -v batfish-data:/data batfish/allinone
    ```

This is all that is needed for Bat-Q, but you can consult the [Batfish installation instructions](https://github.com/batfish/batfish) for other details.


### Bat-Q host

1. Check Python version and install pip3. Bat-Q needs Python 3.11+[cite: 1, 2]:
    ```bash
    $ python3 --version
    $ sudo apt-get install python3-pip
    ```
2. Clone this repository:
    ```bash
    $ git clone https://github.com/martimy/Bat-Q
    $ cd Bat-Q
    ```
3. Install requirements[cite: 1, 2]:
    ```bash
    $ pip3 install -r requirements.txt
    ```
4. Set the environment variable (skip this step if Docker and Streamlit are running on the same machine):
    ```bash
    $ export BATFISH_SERVER=<Batfish server IP address>
    $ echo $BATFISH_SERVER
    ```

    for Windows:

    ```cmd
    Bat-Q>set BATFISH_SERVER=<Batfish server IP address>
    ```
5. Start the Streamlit app (you may need to re-login before this step)[cite: 1, 2]:
    ```bash
    $ streamlit run Home.py
    ```

## User Guide

Here is how to [get started](docs/getting-started.md) using Bat-Q

## Author

Created by Maen Artimy - [Personal Blog](http://adhocnode.com)
