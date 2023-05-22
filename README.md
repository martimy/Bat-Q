# Bat-Q: Network Analyzer with Batfish

This is a Streamlit app that allows you to run network analysis queries using [Batfish](https://www.batfish.org/). The app allows you to select a Batfish question by category and name. The app runs the selected question and displays the results in a table. All answered questions are saved.

## Installation

First, make sure that you have Python 3.6+ and pip installed. Then, you can install the required packages by running:

```bash
pip3 install -r requirements.txt
```


## Usage

To use the app, simply run the following command:

```bash
streamlit run batq.py
```

This will open a Streamlit app in your default web browser.

You will be prompted to enter the path to your network configuration files. Once you enter the path, the app will load all available Batfish questions and display them in the sidebar.

Select a category and a question from the sidebar. The app will display the question description and the selected question. Click on the "Run Query" button to run the question. The app will display the result in a table.

All answered questions are saved in the "Answered Questions" section. You can expand a question to view its description and removed columns.

## Additional Information

Find more information about Batfish questions [here](https://batfish.readthedocs.io/en/latest/index.html).


## Batfish Server Installation

The simplest and most recommended method to install Batfish server is to run a Docker container that houses the Batfish server. In order to run this Docker container, we first need to install Docker on a Linux machine. Docker can be installed on different Linux distributions, and also on macOS and Windows.

These are instruction on how to install Batfish on a Linux machine. This machine needs to have internet connectivity in order to be able to install Docker and pull down the Batfish container.

1. Install Docker on the Linux machine, as demonstrated at this [URL](https://docs.docker.com/desktop/install/ubuntu/).

2. Once Docker is installed and operational, download the Docker container:

```bash
$ sudo docker pull batfish/batfish
```

3. Start the Batfish container (make sure ports 9996 and 9997 are available on the Linux machine):

```bash
$ sudo docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish
```



For more information regarding Batfish and how to install it, see the following URLs:

- https://github.com/batfish/docker
- https://github.com/batfish/batfish/blob/master/README.md


https://pybatfish.readthedocs.io/en/latest/notebooks/interacting.html
