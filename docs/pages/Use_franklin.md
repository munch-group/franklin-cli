## Commands in franklin 

## Students version

To use franklin activate the enviroment were you installed franklin. If you followed the installationguide that enviroment should be called franklin. In order to activate the enviroment use the command below:

conda activate franklin

Then navigate to an empty folder by using the terminal (remember you can use the cd to enter a subfolder, ls to see what is in the subfolder and cd .. to go back to main folder)

After activating your franklin enviroment you can then type franklin in your terminal in order to see the different options in franklin. It should look like this: 
![alt text](<images/Skærmbillede 2025-05-28 kl. 14.37.28.png>)

## Franklin commands

### Download and open exercises
In order to use the commands listed you will first have to type franklin. Thats means if you want to use the download command you will in your terminal write 

franklin download

You will use this command when you want do download an exercise. After running this command a selection menu will pop out and in this menu you will be able to pick between the different courses.
![alt text](<images/Skærmbillede 2025-05-28 kl. 14.52.02.png>)

You choose your course by using the arrow keys and a new selection menu will appear where you can select the specific exercise that you want to do. Franklin then places the downloaded assignment in your the empty folder where you first started franklin. Now before you can do the next step you will have to go to the exercise folder you just downloaded (use cd folder_name_of_exercise)

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



## Educators version
