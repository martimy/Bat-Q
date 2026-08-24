# Getting Started


## Packaging network configuration

Batfish expects network configuration files to be organized in a specific folder structure. The configuration files represent a single snaphost of the network. The folder structures is as follows:

```
snapshot [top-level folder of the name you chose]
    configs [folder with configurations files of network devices]
        router1.cfg
        router2.cfg
        …

    batfish [supplemental information (not device configurations)]
        isp_config.json
        …
```

Bat-Q requires that this folder structure is uploaded as a `.zip` file.

## Home page

At the Home page, you can upload the your network configuration files as `.zip` file. You can upload multiple configuration files. Batfish treats these files as network snapshots. The snapshots can be of the same network at different states or of different networks. Make sure you select one snapshot to be the active snapshot. You may also select another snapshot for comparisons.

![Home Page](pics/home_page.png)

## Questions page

The Questions page displays (almost) all of the Batfish questions grouped in categories. Select the questions you would like to use from the left side of the main screen. The right side of the main screen shows input fields for the selected questions. Most questions accept optional input parameters so there is no need to specify these parameters. Mandatory parameters are denoted by an asterisk.

Use the side bar to save the selected questions (in the Downloads folder, by default). You can also upload previously saved questions from YAML file.

![Questions Page](pics/questions_page.png)

## Analysis page

The Analysis pages shows the answers to the selected questions. Most answers are shown in table format. Bat-Q tries to remove all empty table columns. These removed columns are listed below the table. Topology questions include also a simple diagram of the topology.

![Analysis Page](pics/analysis_page.png)

## Failure Tests page

Batfish allows you to test various network failure scenarios by disabling any number of nodes and/or interfaces in the network. The failed components are included in forked snapshot that Bat-Q assigns a name in "\<snapshot>_fail" format.

Once the failed components are selected, answers to the selected questions will reflect the new state of the network. You can move back-and-forth between the Analysis page and the Failure Tests pages, or even add/delete/modify questions using the Questions pages, as many times as you wish.

![Failure Test Page](pics/failure_page.png)

## Differential page

You can compare two snapshots by selecting them from the Home page. The Differential page shows the answers to the same selected questions but in a slightly different format where the results are shown to belong to the first (Reference) snapshot, the second, or both.

Note that most Batfish questions can be used for single or two snapshots. There are only two questions that can be used for comparisons only.

![Differential Page](pics/differ_page.png)

## Limitations

Bat-Q is not a substitute for pyBatfish, which you will still need to use to get the full power of Batfish. Bat-Q is useful for quick configuration analysis or when writing custom Python code for the network analysis is inefficient or infeasible.