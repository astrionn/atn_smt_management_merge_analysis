from smt_management_app.models import *
import random
import datetime

dbg = False


def run():
    storage = Storage.objects.create(
        name=f"Storage_1",
        capacity=400,
        device=f"{'Dummy' if dbg else 'ATNPTL'}",
        COM_address="COM7",
        ATNPTL_shelf_id=3,
        COM_baudrate=115200,
        COM_timeout=0.4,
    )

    # correct qr codes applied
    storage_slots = []
    for i in range(1, 401):
        qr_val = f"{((i-1) // 50 + 1) * 1000 + ((i-1) % 50 + 1)}"
        storage_slot = StorageSlot.objects.create(name=qr_val, storage=storage)
        storage_slots.append(storage_slot)
        storage_slot.qr_value = qr_val
        storage_slot.save()

    # qr codes for side A and B are switched so 1001 is actually 5001 , 2001 is 6001 and so on
    """ storage_slots = []
    for i in range(1, 401):
        # Calculate the group (1-8) and position within group (1-50)
        group = (i - 1) // 50 + 1
        position = (i - 1) % 50 + 1

        # Calculate the slot name (always the original slot number)
        slot_name = group * 1000 + position

        # Apply the QR swapping logic (first half with second half)
        qr_group = group + 4 if group <= 4 else group - 4
        qr_val = str(qr_group * 1000 + position)

        # Create storage slot
        storage_slot = StorageSlot.objects.create(name=slot_name, storage=storage)
        storage_slots.append(storage_slot)
        storage_slot.qr_value = qr_val
        storage_slot.save() """

    manufacturers = []
    for i in range(1, 4):
        manufacturers.append(
            Manufacturer.objects.create(
                name=f"{['TE Connectivity', 'Weller', 'Samsung'][i-1]}"
            )
        )

    providers = []
    for i in range(1, 11):
        providers.append(
            Provider.objects.create(
                name=f"{["Digi-Key Electronics",
                         "Mouser Electronics",
                         "Arrow Electronics",
                         "Newark Electronics",
                         "Avnet Electronics",
                         "Obeta",
                         "TTI Inc.",
                         "Etronix",
                         "Asia Electronics Corporation",
                         "Farnell"][i-1]}"
            )
        )

    articles = []
    for i in range(1, 6):
        articles.append(
            Article.objects.create(
                name=f"A_{str(i).zfill(3)}",
                description=f"{[
                    "A small surface-mount resistor with a resistance of 100,000 ohms and a tolerance of 1%.",
                    "A small surface-mount inductor with an inductance of 10 microhenries and a tolerance of 5%.",
                    "A small, solid-tantalum capacitor with a capacitance of 10 microfarads and a rated voltage of 6.3 volts.",
                    "A small surface-mount Schottky barrier diode with general-purpose switching characteristics.",
                    "A small surface-mount crystal oscillator that provides a precise 25 MHz clock signal.",
                    "A small voltage regulator chip that provides a stable 3.3 volt output from a higher input voltage.",
                    "A small surface-mount NPN bipolar junction transistor for general-purpose amplification applications.",
                    "A small surface-mount light-emitting diode that emits red light.",
                    "A small, red, surface-mount push-button tact switch.",
                    "A small surface-mount ferrite bead that suppresses electromagnetic interference (EMI) on a circuit."
                ][i-1]}",
                manufacturer=manufacturers[i % 3],
                manufacturer_description=f"{[
                    "Low Resistance Chip Resistor (0603 Case Size, 100kΩ Resistance, ±1% Tolerance)",
                    "Multilayer Ceramic Chip Inductor (10µH Inductance, 0805 Case Size, 5% Tolerance)",
                    "Solid Tantalum Capacitor (SMD A-Series, 10µF Capacitance, 6.3V DC Voltage Rating, 0805 Case Size)",
                    "Schottky Barrier Diode (DO-214AA Surface Mount Package, BAT54S Model Designation)",
                    "Quartz Crystal Oscillator (SMD HC-49S Package, 25MHz Fundamental Frequency)",
                    "Linear Voltage Regulator IC (SMD SOT-23 Package, Fixed Output Voltage of 3.3V)",
                    "Bipolar Junction Transistor (NPN Configuration, SMD SOT-23 Package, BC547 Part Number)",
                    "Light Emitting Diode (SMD Package, 0603 Case Size, Red Emission Wavelength)",
                    "Tactile Dome Pushbutton Switch (SMD Package, 4.0mm x 4.0mm x 2.3mm Footprint, Red Actuation Button)",
                    "Ferrite Bead EMI Suppression Component (SMD Package, 0603 Case Size)",
                ][i-1]}",
                provider1=providers[i % 4 + 1],
                provider1_description=f"{[
                    "Surface Mount Resistor_0603_100kOhm_1%",
                    "SMD Inductor_0805_10uH_5%",
                    "SMD Tantalum Capacitor_A_10uF_6.3V_0805",
                    "SMD Schottky Diode_DO-214AA_BAT54S",
                    "SMD Crystal Oscillator_HC-49S_25MHz",
                    "SMD Voltage Regulator_SOT-23_3.3V",
                    "SMD NPN Transistor_SOT-23_BC547",
                    "SMD LED_0603_Red",
                    "SMD Tactile Switch_SMD-4x4x2.3_Red",
                    "SMD Ferrite Bead_0603_EMI_Suppression"






                ][i-1]}",
                provider2=providers[i % 4 + 2],
                provider2_description=f"{["Precision Chip Resistor_0603_100kOhm_1%",                                      "Surface Mount Inductor_0805_10uH_5%",        "Surface Mount Capacitor_A_Series_10uF_6.3V_0805",        "Surface Mount Schottky Diode_DO-214AA_BAT54S",
                                          "Surface Mount Crystal Oscillator_HC-49S_25MHz",
                                          "Surface Mount Voltage Regulator_SOT-23_3.3V",
                                          "Surface Mount NPN Transistor_SOT-23_BC547",
                                          "Surface Mount LED_0603_Red",
                                          "Surface Mount Tact Switch_SMD-4x4x2.3_Red",
                                          "Surface Mount Ferrite Bead_0603_EMI_Suppression"
                                          ][i-1]}",
                provider3=providers[i % 4 + 3],
                provider3_description=f"{[
                    "SMD Resistor_0603_100kOhm_1%",
                    "0805 Coil Inductor_10uH_5%",
                    "Tantalum Cap SMD_0805_10uF_6.3V",
                    "BAT54S Schottky Diode SMD_DO-214AA",
                    "25MHz Crystal Oscillator SMD_HC-49S",
                    "3.3V Voltage Regulator SMD_SOT-23",
                    "BC547 NPN Transistor SMD_SOT-23",
                    "0603 Red LED_SMD",
                    "4x4x2.3mm Tact Switch SMD_Red",
                    "0603 EMI Suppression Ferrite Bead_SMD"
                ][i-1]}",
                provider4=providers[i % 4 + 4],
                provider4_description=f"{[
                    "0603 Chip Resistor_100kOhm_1%",
                    "Chip Inductor_0805_10uH_5%",
                    "Chip Tantalum Capacitor_A_Series_10uF_6.3V_0805",
                    "DO-214AA Schottky Barrier Diode_BAT54S",
                    "HC-49S SMD Crystal Oscillator_25MHz",
                    "SOT-23 Voltage Regulator_3.3V_SMD",
                    "SOT-23 NPN Transistor_SMD_BC547",
                    "Chip LED_0603_Red_SMD",
                    "Chip Tactile Switch_SMD-4x4x2.3_Red",
                    "Chip Ferrite Bead_0603_SMD_EMI_Suppression"
                ][i-1]}",
                provider5=providers[i % 4 + 5],
                provider5_description=f"{[
                    "1% Tolerance Resistor_0603_100kOhm",
                    "10uH Inductor SMD_0805_5%",
                    "10uF Tantalum Capacitor SMD_A_0805",
                    "SMD Barrier Diode_DO-214AA_BAT54S",
                    "Chip Crystal Oscillator_SMD_HC-49S_25MHz",
                    "SMD Chip Voltage Regulator_SOT-23_3.3V",
                    "Chip NPN Transistor_SMD_SOT-23_BC547",
                    "Red Light Emitting Diode_SMD_0603",
                    "Red Push Button Switch_SMD_4x4x2.3",
                    "EMI Suppression Ferrite Bead_SMD_0603"
                ][i-1]}",
                sap_number=".".join(
                    [
                        "".join([str(random.randint(0, 9)) for _ in range(3)])
                        for _ in range(4)
                    ]
                ),
            )
        )

    carriers = []
    for i in range(1, 11):
        if (i - 1) % 2 == 0:
            j = None
        else:
            j = i
        carriers.append(
            Carrier.objects.create(
                name=f"C_{str(i).zfill(3)}",
                article=articles[i % 5],
                quantity_original=2000,
                quantity_current=random.randint(1000, 2000),
                lot_number=f"Bestellung_{i % 4}",
                # storage_slot=storage_slots[j] if j else None,
                delivered=True,
            )
        )

    board_red = Board.objects.create(name="RedStar IoT Control Board")
    for n, article in zip([10, 2, 4, 3, 1, 1, 5, 8, 3, 6], articles):
        BoardArticle.objects.create(
            name=f"{board_red.name}___{article.name}",
            count=n,
            board=board_red,
            article=article,
        )
    board_green = Board.objects.create(name="GreenWave Sensor Interface Board")
    for n, article in zip([6, 2, 3, 2, 1, 1, 4, 5, 2, 4], articles):
        BoardArticle.objects.create(
            name=f"{board_green.name}___{article.name}",
            count=n,
            board=board_green,
            article=article,
        )

    jobs = []
    for i in range(1, 8):
        jobs.append(
            Job.objects.create(
                name=f"J__{i}",
                description=f"J__{i}",
                customer=f"{[
                "EcoVolt Supply Chain Solutions",
                "BoltStream Logistics",
                "SwiftTech Industrial Services",
                "Globalteck Repair and Maintenance",
                "IntegraNet Industrial Automation",
                "CurEx Power Systems",
                "WireLink Technologies",
                "Amplify Industrial Solutions",
                "SecureGrid Infrastructure Management",
                "DataStream Industrial Diagnostics"
            ][i-1]}",
                project=f"Project {i%2}",
                count=i * 1000,
                board=board_red if i % 2 == 0 else board_green,
            )
        )

    for i, j in enumerate(jobs):
        print(i, j)
        # created
        if i == 0:
            j.description = "Created"
            j.start_at = datetime.datetime.now() + datetime.timedelta(hours=1)
            j.finish_at = datetime.datetime.now() + datetime.timedelta(hours=2)
            j.status = 0
            j.save()
        # assign carriers partial
        if i == 1:
            j.description = "Partially assigned"
            j.start_at = datetime.datetime.now() + datetime.timedelta(hours=2)
            j.finish_at = datetime.datetime.now() + datetime.timedelta(hours=3)
            j.status = 0
            for k in range(5):
                j.carriers.add(
                    Carrier.objects.filter(
                        article=j.board.articles.all()[k], reserved=False
                    ).first()
                )
            j.save()
            for c in j.carriers.all():
                c.reserved = True
                c.save()
        # assign carriers total
        if i == 2:
            j.description = "All assigned"
            j.start_at = datetime.datetime.now() + datetime.timedelta(hours=3)
            j.finish_at = datetime.datetime.now() + datetime.timedelta(hours=4)
            j.status = 1
            for k in range(j.board.articles.count()):
                j.carriers.add(
                    Carrier.objects.filter(
                        article=j.board.articles.all()[k], reserved=False
                    ).first()
                )
            j.save()
            for c in j.carriers.all():
                c.reserved = True
                c.save()
        # # collect carriers
        # if i == 3:
        #     j.description = "collected"
        #     j.start_at = datetime.datetime.now() + datetime.timedelta(hours=3)
        #     j.finish_at = datetime.datetime.now() + datetime.timedelta(hours=4)
        #     j.status = 1
        #     for k in range(j.board.articles.count()):
        #         j.carriers.add(
        #             Carrier.objects.filter(
        #                 article=j.board.articles.all()[k], reserved=False
        #             ).first()
        #         )
        #     j.save()
        #     for c in j.carriers.all():
        #         c.reserved = True
        #         c.storage_slot = None
        #         c.save()
        # # return carriers
        # if i == 4:
        #     j.description = "returned to storage"
        #     j.start_at = (
        #         datetime.datetime.now()
        #         + datetime.timedelta(hours=4)
        #         - datetime.timedelta(days=1)
        #     )
        #     j.finish_at = (
        #         datetime.datetime.now()
        #         + datetime.timedelta(hours=5)
        #         - datetime.timedelta(days=1)
        #     )
        #     j.status = 1
        #     for k in range(j.board.articles.count()):
        #         j.carriers.add(
        #             Carrier.objects.filter(
        #                 article=j.board.articles.all()[k], reserved=False
        #             ).first()
        #         )
        #     j.save()
        #     for c in j.carriers.all():
        #         c.reserved = True
        #         c.storage_slot = None
        #         c.save()

        #     for c in j.carriers.all():
        #         c.storage_slot = StorageSlot.objects.filter(
        #             carrier__isnull=True
        #         ).first()
        #         c.reserved = False
        #         c.save()

        # # note usage
        # if i == 5:
        #     j.description = "Documented actual usage"
        #     j.start_at = (
        #         datetime.datetime.now()
        #         + datetime.timedelta(hours=5)
        #         - datetime.timedelta(days=1)
        #     )
        #     j.finish_at = (
        #         datetime.datetime.now()
        #         + datetime.timedelta(hours=6)
        #         - datetime.timedelta(days=1)
        #     )
        #     j.status = 2
        #     for k in range(j.board.articles.count()):
        #         j.carriers.add(
        #             Carrier.objects.filter(
        #                 article=j.board.articles.all()[k], reserved=False
        #             ).first()
        #         )
        #     j.save()
        #     for c in j.carriers.all():
        #         c.reserved = True
        #         c.storage_slot = None
        #         c.save()

        #     for c in j.carriers.all():
        #         c.storage_slot = StorageSlot.objects.filter(
        #             carrier__isnull=True
        #         ).first()
        #         c.reserved = False
        #         c.save()

        #     for c in j.carriers.all():
        #         c.quantity_current -= i * 6
        #         c.save()

        # # archive
        # if i == 6:
        #     j.description = "archive"
        #     j.start_at = (
        #         datetime.datetime.now()
        #         + datetime.timedelta(hours=5)
        #         - datetime.timedelta(days=1)
        #     )
        #     j.finish_at = (
        #         datetime.datetime.now()
        #         + datetime.timedelta(hours=6)
        #         - datetime.timedelta(days=1)
        #     )
        #     j.status = 2
        #     for k in range(j.board.articles.count()):
        #         j.carriers.add(
        #             Carrier.objects.filter(
        #                 article=j.board.articles.all()[k], reserved=False
        #             ).first()
        #         )
        #     j.save()
        #     for c in j.carriers.all():
        #         c.reserved = True
        #         c.storage_slot = None
        #         c.save()

        #     for c in j.carriers.all():
        #         c.storage_slot = StorageSlot.objects.filter(
        #             carrier__isnull=True
        #         ).first()
        #         c.reserved = False
        #         c.save()

        #     for c in j.carriers.all():
        #         c.quantity_current -= i * 7
        #         c.save()
        #     j.archived = True
        #     j.save()
