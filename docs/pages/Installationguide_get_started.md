## Get started with jupyter note book

### Install Anaconda Navigator
To run Jupyter notebook we will use a distribution of Python called Anaconda. Anaconda is the easiest way of installing Python on Windows, macOS (Mac), and Linux. To install Anaconda, head to [this](https://www.anaconda.com/download) site. Click "Download". When the download has completed, double-click the file you just downloaded and follow the instructions on the screen. It is important that you accept all the suggested installation settings.

### The terminal
You also need a tool to open files and start jupyter notebook. It is also here that you will run franklin in order to download exercises. The terminal will already be installed and is called Terminal on OSX and Anaconda powershell on mac. When you open the terminal it should look like fig 1.1 on mac and fig 1.2 on windows'

![Figure 1.1](<images/Skærmbillede 2025-05-22 kl. 16.44.43.png>)

![Figure 1.2](<images/Skærmbillede 2025-05-22 kl. 16.45.05.png>)

What is Anaconda powershell and this Terminal thing, you ask. Both programs are what we call terminal emulators. They are programs used to run other programs, like the ones you are going to write yourself. In this guide both Terminal and Anaconda Powershel will be refered to as "the terminal"

### Navigating folders via the terminal
The terminal is a very useful tool. To use it, howevever, you need to know a few basics. First of all, a terminal lets you execute commands on your computer. You simply type the command you want and then hit enter. The place where you type is called a prompt. 

When you open the terminal you'll be located in a folder you are in by typing pwd and then press Enter on the keyboard. When you press Enter you tell the terminal to execute the command you just wrote. In this case, the command you typed simply tells you the path to the folder we are in. It would look something like this:

pwd
/Users/kasper/programming 

If the path above was your output you would be in the folder programming. /Users/kasper/programmingis the path or "full address" of the folder with dashes (or backslashes on windows) separating nested
folders. So programmingis a subfolder of kasper which is a subfolder of Users. That way
you not only know which folder you are in but also where that folder is. Let us see what
is in this folder. On OSX you type the ls command (l as in Lima and s as in Sierra)

ls
notes 
projects

It seems that there are two other folders, one called notes and another called projects. If you are curious about what is inside the notes folder, you can "walk" into the folder with the cd command. To use this command you must specify which folder you want to walk into (in this case notes). We do this by typing cd, then a space and the then name of the folder. When you press enter you then get:

cd notes

It seems that nothing really happened, but if I run the pwd command  now to see which folder I am in, I get:

pwd
/Users/kasper/programming/notes


## Install docker and franklin

### What do i need franklin and docker for?

Docker is a tool that makes sure everyone runs the exact same version of a program, no matter what kind of computer they have. When students work on coding assignments, things can sometimes break if they have different versions of Python or other software installed. Docker solves this by creating a special “container” that holds everything the assignment needs — like a mini computer inside your computer. For teachers, this means you don’t have to worry about installing the right packages on every student’s device or assignments suddenly breaking because something got updated. Installing Docker is the first step to making sure your assignments work the same for everyone, every time.

Franklin helps you navigate these containers so that the right "mini computer" is activated when the student works on the exercises that needs that particular enviroment to run

### Install Docker Desktop

In order for franklin to work you also have to download docker desktop

Before you try to download docker, make sure the operating system on your computer has been updated. For docker to run on your device you will have to have Windows newer than Windows 10 or newer than macOS11 (Big Sur) on mac.

If you are downloading docker on a AU computer remember to activate admin priviliges by activating heimdal. 

If you are unsure of how to activate Heimdal follow the instructions given on [this page](https://medarbejdere.au.dk/administration/it/vejledninger/sikkerhed/aktiver-administratorrettigheder-paa-medarbejdercomputer-heimdal)

### Download Docker Desktop on a mac

Go to [this page](https://www.docker.com/products/docker-desktop/) and press on "Download Docker Desktop". When you have done that you will be presented with different options which depends on which chip your computer has. If you do not know, you can find the name of your chip by clicking the apple icon in the upper left corner and choose "about this mac" in the dropdown menu
![alt text](<images/Skærmbillede 2025-06-03 kl. 13.28.40.png>)

Apple silicon chips include M1, M2 and M3. 
Apple intel chips are named intel.

Back on the docker desktop download page you choose the one that matches your computer chip and follows the instruction on your device. You have to click accept when your computer asks you if you trust the provider. When docker desktop opens a window pops up and asks if you want to sign in or create and account. You can just press skip on these. An account is not necessary for using docker in franklin.

When docker desktop is done downloading shut down the program. Make sure that it has been compleately shut down by checking the top right corner of your device. If there is an icon that looks like a small cargo ship click on it and choose "Quit Docker Desktop" in the dropdown menu
![alt text](<images/Skærmbillede 2025-06-03 kl. 14.27.12.png>)

### Download Docker Desktop on a Windows

Go to [this page](https://www.docker.com/products/docker-desktop/) and press on "Download Docker Desktop". When you have done that you will be presented with different options which depends on which chip your computer has. If you do not know, you can find the name of your chip by right clicking on the start button and click system. Under device specifications look for processor. This will tell you the chip name and whether it is a AMD chip or an ARM chip

Back on the docker desktop download page you choose the one that matches your computer chip and follows the instruction on your device. You have to click accept when your computer asks you if you trust the provider. When docker desktop opens a window pops up and asks if you want to sign in or create and account. You can just press skip on these. An account is not necessary for using docker in franklin.

When docker desktop is done installing make sure the program is compleately shut down. You do this by going to "Taskmanager" and search for "docker" in the search bar in taskmanager. If there is any tasks open where docker is involved click "End task"

If docker desktop comes with the error message "WSL 2 is required"
Install WSL via copying the following command into your terminal:

wsl --install

## Enviroments

In bioinformatics, we install packages and programs so we can use them in our analyses and pipelines. Sometimes, however, the versions of packages you need for one project conflicts with the versions you need for other projects that you work on in parallel. Such conflicts seem like an unsolvable problem. Would it not be fantastic if you could create a small insulated world for each project, which then only contained the packages you needed for that particular project?. If each project had its own isolated world, then there would be no such version conflicts. Fortunately, there is a tool that lets you do just that, and its name is Conda.

“Conda is an open source package management system and environment  management system for installing multiple versions of software packages and their dependencies and switching easily between them. ”

The small worlds that Conda creates are called "environments". You can create as many environments as you like, and then use each one for a separate bioinformatics project, a course, a bachelor project, or whatever you would like to insulate from everything else. Conda also downloads and installs the packages for you and it makes sure that the software packages you install in each environment are compatible. It even makes sure that packages needed by packages (dependencies) are also installed. Conda is truly awesome.

In this case you need to create a new enviroment where you install franklin

You will need franklin for downloading assignments. You will also be able to choose a enviroment in franklin that specifially fits the assignment you want to make.

### Create Franklin enviroment and install franklin
In order to download franklin and install an enviroment called franklin you have to write the code below into your terminal

conda create -y -n franklin -c conda-forge -c munch-group franklin

This commands runs the Conda program and tells it to create a new enviroment with the name franklin and to install franklin in that enviroment. Once you have ran the command, your terminal output should look something like this:

[output](<images/Skærmbillede 2025-05-25 kl. 15.19.24.png>)

### Franklin for educators
You will then also need to download franklin educator 
Before you insert the code below, activate your franklin enviroment in your terminal 

conda activate franklin

conda install -c conda-forge -c munch-group franklin franklin-educator

Every time you want to start franklin you use the command 

conda activate franklin

## set up gitlab
### What do i need gitlab for?
GitLab is a website where you can store and share your code and teaching materials — kind of like Google Drive, but built for programming. When you put your exercises on GitLab, you always have a clear and organized version of your work that others (like students) can access. When using Docker, GitLab becomes especially useful because you can keep everything in one place: the exercise instructions, the Docker setup, and the files students need. This makes it easy to update, reuse, and share your assignments

### sign in
Go to gitlab by following [this link](https://gitlab.au.dk)
On the sign-in page, choose the login option called login with Uni-add. 

### SSH keys - what is that and why do i need it?
SSH keys are a secure way to log in to remote systems or services without needing to enter a password each time. An SSH key works like a digital lock and key system. The private key is kept safely on your computer, while the matching public key is shared with the service you want to access. When you try to connect, the service checks that your private key matches the public one it has on file. If they match, access is granted automatically—no password required.

### How do i get a SSH key?

First, check if you have these two authentication files on your local machine:

~/.ssh/id_rsa
~/.ssh/id_rsa.pub
You can do so using the ls commmand:

ls -a ~/.ssh

You most likely do not. If so, you generate authentication keys with the command below. Just press Enter when prompted for a file in which to save the key. Do not enter a passphrase when prompted - just press enter:

ssh-keygen -t rsa

Now use ssh to create a directory ~/.ssh on the cluster (assuming your username on the cluster is <cluster user name>). SSH will prompt you for your password.

ssh <cluster user name>@login.genome.au.dk mkdir -p .ssh

Finally, append the public ssh key on your local machine to the file .ssh/authorized_keys on the cluster and enter your password (replace <cluster user name> with your cluster user name):

cat ~/.ssh/id_rsa.pub | ssh username@login.genome.au.dk 'cat >> .ssh/authorized_keys'

### insert SSH key to gitlab
To access your SSH keys you use the command: 

cat ~/.ssh/id_rsa.pub

It is very important that you choose the rsa.pub version.

After you have run the command cat ~/.ssh/id_rsa.pub in your terminal  a long line of letters and number will appear in your terminal. This is your SSH key. 
Now copy it and go back to the [gitlab webpage](https://gitlab.au.dk) 

Then press the icon on the top beside the picture that represent your profile and find the option called "edit profile" in the dropdown menu
It should look like this: ![alt text](<images/Skærmbillede 2025-05-27 kl. 13.42.11.png>)

Now you should be able to see an option in the left side menu called ‘add new ssh key’. You press that and then you insert the copied ssh-key in the box.

The page should look something like the figure below:
![alt text](<images/Skærmbillede 2025-05-27 kl. 13.40.10.png>)

In the bottom of the page, you can write an expiration date of your SSH key. In order to not have to enter a new SSH key, you can remove this. 

You are now ready to use gitlab!


## Start franklin
To use franklin activate the enviroment were you installed franklin. If you followed the installationguide that enviroment should be called franklin. In order to activate the enviroment use the command below:

conda activate franklin

Then navigate to an empty folder by using the terminal (remember you can use the cd to enter a subfolder, ls to see what is in the subfolder and cd .. to go back to main folder)

After activating your franklin enviroment you can then type franklin in your terminal in order to see the different options in franklin. It should look like this: 
![alt text](<images/Skærmbillede 2025-05-28 kl. 14.37.28.png>)


## Guide to create exercises in franklin

Educators with limited computational skills can develop and distribute jupyter exercises that will run year on year on the the diverse Mac and Windows computers of large cohorts of students.

Running the following command prompts the educator for course and exercise name and creates a new exercise.

franklin exercise new

When you have used this command the terminal will guide you thorugh how you make a new exercise. It will first ask you to write a name of your exercise in the terminal and then open gitlab where you can make a description. The you will go back to your terminal when it tells you to and run the commands

franklin exercise edit

This command lets you edit your new exercise, launches jupyter in an appropriate environment, waits while the educator edits the notebook, and then automatically makes the edited notebook available to students in an environment automatically generated to accommodate any new dependencies resulting from changes to the notebook.

## Other franklin commands

### download an exercise without editing.

If you want to download an exercise the same way the students does it, you can use the command

franklin download

After running this command a selection menu will pop out and in this menu you will be able to pick between the different courses.
![alt text](<images/Skærmbillede 2025-05-28 kl. 14.52.02.png>)

You choose your course by using the arrow keys and a new selection menu will appear where you can select the specific exercise that you want to download. Franklin then places the downloaded assignment in your the empty folder where you first started franklin. Now before you can do the next step you will have to go to the exercise folder you just downloaded (use cd folder_name_of_exercise)

Then in order to make sure can run code in the exercise you run the command:

franklin jupyter 

A new selection menu now opens that once more shows you the different courses. Use the key arrows to pick your course and in the submenu pick the exercise you want to solve. Jupyter notebook now opens in your browser. in the filemenu on the right side in jupyter you should be able to see your newly downloaded exercise. Open it and your ready to go!

Note: If the message below pops up, the folder you started franklin in was either not empty or you may have forgotten to go to the exercise subfolder![alt text](<images/Skærmbillede 2025-05-28 kl. 15.22.07.png>)

### Clean up old docker containers
In order or your TØ exercises to run correctly an enviroment that is the same for each students computer is created in docker. These are also specific for each course and exercise. Unfortunately, these take up a fair ammount of space on your computer, so when you are done with a course it might be a good idea to delete these. 

You can easily do this by using the command franklin cleanup

run the command: 
franklin cleanup

A seletion menu will then appear with all your currently downloaded docker images, named after each of your exercises. You can then use your arrow keys to select the exercise enviroments that you no longer use. 

![alt text](<images/Skærmbillede 2025-05-28 kl. 15.32.16.png>)

Note: deleting the exercise enviroments like this DO NOT delete the exercise you have made yourself and of you would ever need a specific enviroment for an old exercise again, you simple download it once more.

### Update franklin
Franklin should update automaticaly when you start the program, but if you should need to update it manually you can use the command 

franklin update

You can also check out which version of franklin you have installed by using the command 

franklin --version
