# ATN SMT MANAGEMENT

This application assists three real life workflows to receive, store and use SMD materials in an industrial SMT process to manufacture *boards*.

*Boards* are manufactured in a *machine* from multiple *carriers* each storing an amount of an *article*.

Each *board* is represented as a a list of *article*-count pairs, this is also called bill of materials.

*Carriers* need to be ordered from a *provider*, received, stored and collected for a *job*, used in a *job* and re-stored or discarded.
The ordering part is outside the scope of this application. The user imports orders of *carriers* after the order process has been done in real life.

*Carriers* usually have the dimension of a cylinder and have properties like diameter and width. This is relevant for storing in a *storage* or a *machine* .
A *carrier* is identified by its UID, a sticker/label containg the UID and a QR Code of the UID is placed on the carrier by the user after an order of *carriers* is delivered at the manufacturing facility but before they are stored..

A *provider* is the entity that delivers *carriers* to the manufacturing facility.


A *manufacturer* is the entity that produces *carriers* that are delivered by a *provider*.


A *carrier* can be stored in the *storage* *slot* of a *storage* or the *machine* *slot* of a *machine*. 

A *job* is manufacturing a *board* a number of times in a certain time frame. A *job* can be part of a *project* and can have *customers*.


A *machine* is a pick'n'place machine it produces *boards* from *carriers*. Akin to a 3D printer, which uses filament to print objects layer by layer, a pick'n'place *machine* "prints" *boards* *article* by *article*.
Like *storage*, a *machine* has *machine* *slots*.

A *storage* is a shelf with *storage* *slots*, each slot has an LED that can be activated by this application.
## Backend( Django )


#### Requirements

Open terminal in specific direcotry

To make virtual environment using
```
python -m venv venv

Activate environment

For Windows:
./venv/Script/activate

For MACOS:
source ./venv/bin/activate
```

To install requirements type

```
pip install -r requirements.txt
```


To migrate the database open terminal in project directory and type

```
python manage.py makemigrations
python manage.py migrate
```


To run the program in local server use the following command

```
python manage.py runserver
```


Server will be available at `http://127.0.0.1:8000` in your browser



##                                                    

The backend will be provided with the django library in python 3.11 64bit
It is contained in the *python* folder.


- choose which shelf device is needed

  There are 3 different libraries for 3 different shelfs at the moment.
  
  Neolight Smart Shelf(neolight_handler.py) , Sophia PTL (xgatehandler.py) and ATNs own implementation PTLHandler.py

  For developement purposes you can find a dummy class at the top of views.py, modify accordingly.

 - enable/disable the label printer

   for developement I highly recommend not enabling the printer, you can find it in the same try/catch block at the top of views.py

### Notes for refactoring
does carrier fit into slot for storage?

****Frontend****
Initial Draft containing description of functionality, API templates, Screenshots

****login****
The user starts with a simple login form.

****plain****
![1](https://github.com/astrionn/atn_smt_management/assets/65600488/049f6147-ad60-40e3-9a3a-92a90c817341)

**** login failed ****
![2](https://github.com/astrionn/atn_smt_management/assets/65600488/3c89ea45-3c8f-4d74-a5a5-4a7f79fb23c5)

****dashboard****
Upon login the user gets to the dashboard which presents usefull data like outstanding deliveries, storage capacity and the number of open jobs.

From there the user can navigate to the 4 main pages: dashboard, material entry, material storage and setup center.

The admin tile wont be required.

The tiles should be clickable and redirect to the other pages.

The left sidebar contains routing buttons to the 4 pages(dashboard,material entry, material storge, setup center).


![3](https://github.com/astrionn/atn_smt_management/assets/65600488/0f45be0a-9128-4e64-a3ed-1372747421b6)


****material entry****
This page facilitates three main functions, entering new orders into the system, tracking order status and marking carriers as delivered.


An order is usually a comma seperated list of carriers, rarely it is a singular carrier.


The user can enter an order into the system by uploading a csv file containing the ordered carriers row by row, each row representing one carrier.
The first row, as an exception, should contain the column headers names of the file, which do not have to match the form fields.


If the user uploads a csv file via the import button, he is then tasked to map the form field names to the column headers of the csv file.


This mapping is remembered and will be provided as default values for future mappings.


The user can also add a singular carrier via a form.


One carrier always only carries one type of article.
Therefore before a carrier can be created the article needs to be created.


The main body of the page is a table displaying all carriers even the ones that have been ordered and not yet delivered.
The table supports filtering by column criteria like delivery status or lot number.

In the header of the table is a field which would usually be a search bar but it provides a way to tick the selection box of a row.

#+begin_example
If there is a value entered and confirmed with return, the row which has the entered value as the carrier uid field is added to the selection, i.e. the selection box of that row is ticked.

Entering the carrier UID and pressing enter will be beformed by a handheld scanner, this enables quickly selecting carriers in the table by scanning their QR Codes in real life.
#+end_example

The header of the table also provides 3 actions for the selected rows and 2 general actions.

- The selection can be set as delivered.
- The selection can be printed. (labels containg the carrier UID as a QRCode)
- The selection can be deleted.



The next table header button allows hiding/showing the columns of the table.
The final button exports the current view of the table, kind of like a screenshot, has nothing to do with the selection.


The workflow is as follows:

1. Order carriers and receive an order number outside of this application
2. Add carriers via form or file, supplying the order number as lot number
3. Wait for arrival of order
4. Filter carriers by ~lotnumber=order number~ and ~delivered=False~

   The user will upon receiving a delivery filter for the delivery number, or lotnumber.
   He may narrow it down further by filtering for e.g. manufacturer or provider.
   If a delivery only has been partially processed the user may filter for delivery status.
5. Select all and print the labels.

   Printing a selection deselects all carriers and places the cursor in the "search box".
6. Stick a label on the carrier and scan it (row gets selected)
   The user steps away from the application only having a handheld scanner as remaining input device to the application.
   The user then proceeds to stick a sticker on the corresponding carrier.
   The user uses the scanner and scans the qr code on the label that just has been placed on the carrier, this selects the row of the carrier in the application.
7. repeat 6. until all labels are used
8. set selection as delivered
   The user returns to the application and sees all teh carriers he has just labelled selected in the table.
   The user presses the icon with the little arrow in the toolbar of the table, this changes the status of delivered from False to True.
   Delivering a selection resets all filters of the table.
****screens****
****plain****

![4](https://github.com/astrionn/atn_smt_management/assets/65600488/491804d0-842a-4aa0-9897-7d8cfb9e3a7b)


****add single article****
![5](https://github.com/astrionn/atn_smt_management/assets/65600488/a565963e-44e9-4873-b079-442988b0894e)

****success****
no screenshot : snackbar notification in green with success message

****fail - form****
![5a](https://github.com/astrionn/atn_smt_management/assets/65600488/4a3ce0e2-566a-4fc9-97ac-19e785d68375)

****fail - server****
no screenshot : snackbar notification in red with error message

****add csv articles****
The first click opens a file upload window, afterewards the column selector.
![8](https://github.com/astrionn/atn_smt_management/assets/65600488/927fda73-1c37-4597-ba07-3cd2ca9af87f)

****success****
im open for a better way to design the notification
![8a](https://github.com/astrionn/atn_smt_management/assets/65600488/6f65b17c-582b-4e59-adb9-bf02462b442a)


****fail - file upload****
general file upload error
****fail - server****
error while processing the file since data is malformed or not well defined


****add single carrier****
see add single article
****success****
****fail - form****
****fail - server****

****add csv carriers****
see add csv carriers
****success****
****fail - file****

****fail - server****


****with data****
ignore the snackbar notification on the bottom
![8a](https://github.com/astrionn/atn_smt_management/assets/65600488/54f460f1-a314-4c53-9ea9-b4737d9203e4)


****material storage****
This page facilitates the users physical interaction with the storages. Mainly adding a carrier to a storage, collecting a carrier from a storage, deleting a carrier and collecting multiple carriers at once.


A storage consists of storage slots each with an unique id, each slot also has an LED and a qrcode with the storageslot ID.


Delivered carriers can be stored in the selected storage by entering their UID into the add field and pressing return.


The user is then presented with a popup, within the ID of a storageslot is displayed.
The LED of that storageslot is blinking green while the popup is displayed.


The user is expected to put the carrier into the slot with the blinking LED and is expected to scan the QR code of the slot, containing its ID.
The scanning action is the same as the user inputing the slots ID via the keyboard and pressing enter.


Closing the popup cancels the attempt to add to storage and kills teh LED.
If the user scans/enters the wrong slot ID, he can try again until success. 


A carrier can be displayed via the display field. The carrier data is editable and saveable. The label is printable from here. The LED is turned green while displaying component is mounted.


A carrier can be retrieved from storage by entering their UID in the collect field.


The corresponding storage and storageslot will be displayed to the user and the LED will start blinking blue until its storageslot ID has been scanned.


If there are multiple carriers being collected a queue is displayed showing the storage slots which have not been scanned.
This queue can also be filled with the collect job field after finishing the pre-setup step of the setup center workflow.


The queue should be a collapsable text field containing carrier UIDs - storage slot IDs pairs.
It displays all the carriers that have been added to the queue whose corresponding storage slot ID has not been scanned.


Scanning a storage slot ID removes it from the queue and kills the LED.


A carrier can also be deleted from the system - when its discarded in real life.


The main body of the page shows the different storages and machines and their contents in collapsable tables.


The tables support the same functionality as the previous tables including the not-search-but-select box and header buttons to collect, delete or display(just LEDs) the selection.



****plain****
![9](https://github.com/astrionn/atn_smt_management/assets/65600488/5f8a7b51-3011-44e2-bec7-cf623900d90e)


![10](https://github.com/astrionn/atn_smt_management/assets/65600488/4cf140cb-abff-490a-8ca0-171a34e5c908)

****plain with some data in a shelf****

![11](https://github.com/astrionn/atn_smt_management/assets/65600488/b319d91e-a275-4659-8db2-a23692098324)


****display carrier****
![12](https://github.com/astrionn/atn_smt_management/assets/65600488/0c44565b-4abf-4b9a-8741-8c754501d5d0)


****edit carrier****
no screenshots, editable fields, some with suggestions others type restrictions
success and fail messages via colored snackbar
****success****
****fail****

****add****

****confirm slot****
no screenshot, popup component indicating the storage and slot to scan.

****success****

![14](https://github.com/astrionn/atn_smt_management/assets/65600488/dfff9d3f-a57e-4a14-8b66-e22d2f9d63bb)


****fail****

![13](https://github.com/astrionn/atn_smt_management/assets/65600488/c3430101-c050-4338-8546-963865881296)
![15](https://github.com/astrionn/atn_smt_management/assets/65600488/160acdab-98dd-49e9-a36e-59633d6f4524)


****collect****
In this example at least 3 carriers are in the collect queue, if any of the corresponding storageslot IDs is scanned it is taken from the queue and the correspondance is lifted.

If another carrier UID would be entered the queuecount would increase to 5 and a snackbar notification with the storageslot info gets shown.

A way to list the actual UIDs in the queue would be nice, refer to above.

Just for clarification: it is not an actual queue but a set, but the terminology is established already.

![18](https://github.com/astrionn/atn_smt_management/assets/65600488/e7be6ec7-a558-42ce-b0e2-5b5419005c95)

****success****
no screenshot.
green snackbar notification that indicates scanning of the correct slot,  table update


****fail****
****carrier not found****

![17](https://github.com/astrionn/atn_smt_management/assets/65600488/4290314f-561f-4a8e-a34c-44d648552767)


****wrong slot scanned try again****

slot contains no carrier in the collect queue 

****delete****
****success****
![16](https://github.com/astrionn/atn_smt_management/assets/65600488/870d4142-8c11-4352-825b-c6197d5ce260)


****fail****
****carrier doesnt exist****
![17](https://github.com/astrionn/atn_smt_management/assets/65600488/ffa81df3-43d0-4c23-9857-aed759755c87)

****setup_center****
This page facilitates creating jobs, allocating carriers to them and finishing them.

The basis of each job or board is a list of article-count pairs.

This list can be provided as a csv file or entered manually.

Additionally a job has an assigned machine, time slot, a count and a status.

After a job with his parameters has been created a carrier for each article needs to be chosen which will be marked as reserved - this is called pre-setup.

Once the pre-setup is complete the carriers of a job can be collected from the material_storage page.

After that the production process in the real world happens.
After the job is finished the user provides the actual usage of articles for each carrier and an optional note.
By marking a jopb conpleted the carriers are no longer marked as reserved and need to be restored, discarded or left on the machine for the next job if applicable.


The typical user workflow looks like this:

1. create job
2. assign carriers to job
3. collect carriers
4. do the production process in the real world
5. mark job as completed and note usage
6. re-store the carriers


****plain****

![20](https://github.com/astrionn/atn_smt_management/assets/65600488/1b7ac88b-dbed-4809-aae5-3ed483f63e12)


****create job****
![21](https://github.com/astrionn/atn_smt_management/assets/65600488/8f77ed0e-6ca9-4c34-a768-2fbb49d38881)
![22](https://github.com/astrionn/atn_smt_management/assets/65600488/fecaea20-3d0b-4feb-b75f-c84766369c9f)
![25](https://github.com/astrionn/atn_smt_management/assets/65600488/fa9f2733-7933-4461-9307-c1c9c3c3cf1b)

t****ime and date picker****
![23](https://github.com/astrionn/atn_smt_management/assets/65600488/5e5c5c40-90dd-4095-a5ae-057534d2e988)


****timeline of scheduled jobs****

![31](https://github.com/astrionn/atn_smt_management/assets/65600488/a30940c5-e6a7-4ac0-8bbe-14ef45958a46)


****upload csv****

no screenshot, but same as on material entry: first the user uploads a file and then a component is mounted so the user can map column headers to field names
with according snackbar notifications
****fail****

****input error****

![24](https://github.com/astrionn/atn_smt_management/assets/65600488/d509f3b3-81f4-414c-b335-0dcd9bc3d732)


****server file error****

notification with error

****pre setup****
add  progressbar

entry = article entry on the left side
****BOM no entry selected****

![26](https://github.com/astrionn/atn_smt_management/assets/65600488/0511f0b3-2c73-4ee2-8cde-826f2408953b)


****BOM entry selected****
shows available carriers
****carriers displayed, some with warning****
![27](https://github.com/astrionn/atn_smt_management/assets/65600488/4dbd46d3-9f30-49f6-aca1-dfc896ea80c1)


****no carriers available****
![1](https://github.com/astrionn/atn_smt_management/assets/65600488/ffb86bf5-d472-4ae1-973a-6527fea4c9ef)


****carrier selected****
![28](https://github.com/astrionn/atn_smt_management/assets/65600488/6d8e25c7-5d96-463c-8295-e4e608d088b7)

****all carriers selected****
![32](https://github.com/astrionn/atn_smt_management/assets/65600488/65688d7a-3bc1-428a-8a77-3203be6bc006)



****finish job****
![29](https://github.com/astrionn/atn_smt_management/assets/65600488/aefe93c1-4a77-42fe-a071-f9ee95ba32f8)


****multiple jobs with different color coding based on state: scheduled, pre-setup-done, collected, finished****
![30](https://github.com/astrionn/atn_smt_management/assets/65600488/d413a4de-c2e3-4b4b-b1af-00bab253df04)


## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
