# Net-Q - Network Analyzer with Batfish

This is a Streamlit app that allows you to run network analysis queries using [Batfish](https://www.batfish.org/). The app allows you to select a Batfish question by category and name. The app runs the selected question and displays the results in a table. All answered questions are saved.

## Installation

First, make sure that you have Python 3.6+ and pip installed. Then, you can install the required packages by running:

```bash
pip3 install -r requirements.txt
```


## Usage

To use the app, simply run the following command:

```bash
streamlit run st_batfish.py
```

This will open a Streamlit app in your default web browser.

You will be prompted to enter the path to your network configuration files. Once you enter the path, the app will load all available Batfish questions and display them in the sidebar.

Select a category and a question from the sidebar. The app will display the question description and the selected question. Click on the "Run Query" button to run the question. The app will display the result in a table.

All answered questions are saved in the "Answered Questions" section. You can expand a question to view its description and removed columns.

## Additional Information

Find more information about Batfish questions [here](https://batfish.readthedocs.io/en/latest/index.html).
