NioCommand
===========
Command a nio service or block in a running nio service.

One request is made for every input signal. For each successful request, an output signal is created with the json response (if response was json) or a signal with a `resp` attribute.

Properties
--------------
-   **service**: Name of service to command.
-   **block**: Name of block to command. If blank, then the service will be commanded.
-   **command**: Name of service or block command.
-   **params**: Key/Value pairs to pass as parameters to the command.
-   **host**: Location of nio instance.
-   **port**: Port of nio instance.
-   **security_method**: HTTP Method (ex. NONE, BASIC (default), OAUTH).
-   **basic_auth_creds**: When using Basic Authentication, enter the username and password.
-   **private_key**: When using OAuth, enter the location of the Service Account JSON key file. The path is relative to the root of the nio project. (ex. `etc/private_key.json`)

Dependencies
----------------
- oauth2client
- pycrypto or pyopenssl

## Getting Started with OAuth

In order to command a nio instance secured by OAuth you will need a Google Service Account and access to its JSON key.

1. Go to the [Google Developers Console](https://console.developers.google.com/). Select your project (or create one!)
2. Go to **APIs & Auth** > **Credentials**
3. Click on **Create new Client ID**
4. Select **Service Account** and wait for the key pair to be created.
5. Write down the email address that is created.
5. Once created, click **Generate new JSON Key** and download and save the JSON file. 
6. Place this file in one of the following locations, and note the filename:
  - Next to the block file
  - In the project directory (the default block setting is to put the file at the root of the nio project and name the file `private_key.json`)
7. In the block config, put the location of the file in the **Private Key Config File** config.
8. Grant access to the Service Account in the nio project that will be commanded. In the target nio project, add the email address from step 5 to the list of users in `etc/roles.dat`. Set the access groups that this user should belong to.

Commands
----------------
None

Input
-------
Any list of signals.

Output
---------
One output signal will be created for each command (and therefore one fore each input signal).

If the command response is json, then the Signal representation of the json will be emitted.

If the command response is not json, then the Signals will have an attribtue `resp` with the text representaion of the response as the value.
