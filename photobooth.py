"""This module simulates a photobooth.
See instructions at http://www.drumminhands.com/2014/06/15/raspberry-pi-photo-booth/"""
# created by chris@drumminhands.com
# modified by sproctor@gmail.com

import atexit
import glob
import os
import sys
import socket
import time
import traceback

import cups
import RPi.GPIO as GPIO
import picamera
import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE
import pytumblr # https://github.com/tumblr/pytumblr

import config # this is the config python file config.py

########################
### Variables Config ###
########################
LED_PIN = 7 # LED
BTN_PIN = 18 # pin for the start button

TOTAL_PICS = 4 # number of pics to be taken
CAPTURE_DELAY = 3 # delay between pics
PREP_DELAY = 5 # number of seconds for users prep for photos, minimum 2 seconds to warm up camera
GIF_DELAY = 100 # How many milliseconds between frames in the animated gif
RESTART_DELAY = 2 # how long to display finished message before beginning a new session
REPLAY_DELAY = 5 # how much to wait in-between showing pics on-screen after taking
TEST_SERVER = 'www.google.com'

####################
### Other Config ###
####################
REAL_PATH = os.path.dirname(os.path.realpath(__file__))

#################
### Functions ###
#################


# clean up running programs as needed when main program exits
def cleanup():
    pygame.quit()
    GPIO.cleanup()


atexit.register(cleanup)


def post_button_event():
    pygame.event.post(BUTTON_PRESS_EVENT)


def turn_on_led():
    GPIO.output(LED_PIN, True)


def turn_off_led():
    GPIO.output(LED_PIN, False)


def blink_led(count):
    for _ in range(0, count):
        turn_on_led()
        time.sleep(0.25)
        turn_off_led()
        time.sleep(0.25)


#delete files in folder
def clear_pics():
    files = glob.glob(config.file_path + '*')
    for f in files:
        os.remove(f)
    #light the lights in series to show completed
    print("Deleted previous pics")
    if not config.have_monitor:
        blink_led(3)


# check if connected to the internet
def is_connected():
    try:
        # see if we can resolve the host name -- tells us if there is a DNS listening
        host = socket.gethostbyname(TEST_SERVER)
        # connect to the host -- tells us if the host is actually
        # reachable
        socket.create_connection((host, 80), 2)
        return True
    except:
        pass
    return False

def scale(orig_size, desired_size, maximum=True):
    w, h = orig_size
    x, y = desired_size
    nw = y * w // h
    nh = x * h // w
    if maximum ^ (nw >= x):
        return nw or 1, y
    return x, nh or 1


def get_offsets(object_size, surface_size):
    obj_w, obj_h = object_size
    surf_w, surf_h = surface_size
    return (surf_w - obj_w) // 2, (surf_h - obj_h) // 2


def aspect_scale(img, desired_size):
    """ Scales 'img' to fit into box bx/by.
     This method will retain the original image's aspect ratio """
    scaled_size = scale(img.get_size(), desired_size)
    return pygame.transform.scale(img, scaled_size)

# display one image on screen
def show_image(image_path):
    #print('Show image: ' + image_path)
    # clear the screen
    SCREEN.fill((0, 0, 0))

    # load the image
    img = pygame.image.load(image_path)
    scaled_img = aspect_scale(img, SCREEN.get_size())
    SCREEN.blit(scaled_img, get_offsets(scaled_img.get_size(), SCREEN.get_size()))
    pygame.display.flip()


# display a blank screen
def clear_screen():
    SCREEN.fill((0, 0, 0))
    pygame.display.flip()


def create_collage(jpg_group, img_size):
    # FIXME: this only works for 4 pictures
    i = 1
    img_w, img_h = img_size
    desired_size = img_w // 2, img_h // 2
    collage = pygame.Surface(img_size)
    for y in range(2):
        for x in range(2):
            img = pygame.image.load(config.file_path + jpg_group + "-0" + str(i) + ".jpg")
            i += 1
            scaled_img = pygame.transform.scale(img, desired_size)
            offset_x = x * img_w // 2
            offset_y = y * img_h // 2
            collage.blit(scaled_img, (offset_x, offset_y))
    return collage

# display a group of images
def display_pics(jpg_group):
    # FIXME: this only works for 4 pictures
    i = 1
    screen_w, screen_h = SCREEN.get_size()
    desired_size = screen_w // 2, screen_h // 2
    for y in range(2):
        for x in range(2):
            img = pygame.image.load(config.file_path + jpg_group + "-0" + str(i) + ".jpg")
            i += 1
            scaled_img = aspect_scale(img, desired_size)
            offset_y, offset_x = get_offsets(scaled_img.get_size(), desired_size)
            offset_x += x * screen_w // 2
            offset_y += y * screen_h // 2
            SCREEN.blit(scaled_img, (offset_x, offset_y))
    pygame.display.flip()
    time.sleep(REPLAY_DELAY)

def init_camera():
    print('Init camera')
    camera = picamera.PiCamera()
    camera.vflip = False
    camera.hflip = True # flip for preview, showing users a mirror image
    if config.black_and_white:
        camera.saturation = -100
    #camera.iso = config.camera_iso
    return camera


def display_instructions():
    print("Get Ready")
    turn_off_led()
    show_image(REAL_PATH + "/instructions.png")
    time.sleep(PREP_DELAY)


def take_pictures(camera, jpg_group):
    print("Taking pics")

    for i in range(1, TOTAL_PICS + 1):
        camera.hflip = True # preview a mirror image
        camera.start_preview()
        for n in range(CAPTURE_DELAY, 0, -1):
            img = pygame.image.load(REAL_PATH + "/pose" + str(n) + ".png")
            scaled_img = pygame.transform.scale(img, (96, 64))
            overlay = camera.add_overlay(pygame.image.tostring(scaled_img, 'RGB'),
                                         size=(96, 64), format='rgb', layer=3,
                                         fullscreen=False, window=(0, 0, 96, 64))
            time.sleep(1)
            camera.remove_overlay(overlay)
        # Make the screen white
        SCREEN.fill((255, 255, 255))
        pygame.display.flip()
        camera.stop_preview()
        turn_on_led()
        time.sleep(0.25)
        filename = config.file_path + jpg_group + '-0' + str(i) + '.jpg'
        camera.hflip = False # flip back when taking photo
        print('Saving: ' + filename)
        if config.hi_res_pics:
            camera.capture(filename)
        else:
            camera_w, camera_h = camera.resolution
            pixel_width = 500 # maximum width of animated gif on tumblr
            pixel_height = camera_h * pixel_width // camera_w
            camera.capture(filename, resize=(pixel_width, pixel_height))
        turn_off_led()


def create_gif(jpg_group):
    print("Creating an animated gif")
    show_image(REAL_PATH + "/processing.png")
    if config.hi_res_pics:
        # make a small version of each image. Tumblr's max animated gif's are 500 pixels wide.
        for x in range(1, TOTAL_PICS + 1): #batch process all the images
            os.system("gm convert -size 500x500 " + config.file_path + jpg_group + "-0"
                      + str(x) + ".jpg -thumbnail 500x500 " + config.file_path + jpg_group
                      + "-0" + str(x) + "-sm.jpg")

        os.system("gm convert -delay " + str(GIF_DELAY) + " " + config.file_path + jpg_group
                  + "*-sm.jpg " + config.file_path + jpg_group + ".gif")
    else:
        # make an animated gif with the low resolution images
        os.system("gm convert -delay " + str(GIF_DELAY) + " " + config.file_path + jpg_group
                  + "*.jpg " + config.file_path + jpg_group + ".gif")


def upload_photo(jpg_group):
    # Setup the tumblr OAuth Client
    client = pytumblr.TumblrRestClient(
        config.consumer_key,
        config.consumer_secret,
        config.oath_token,
        config.oath_secret,
    )

    show_image(REAL_PATH + "/uploading.png")
    connected = is_connected() #check to see if you have an internet connection

    if not connected:
        print("bad internet connection")

    while connected:
        if config.make_gifs:
            try:
                file_to_upload = config.file_path + jpg_group + ".gif"
                client.create_photo(config.tumblr_blog, state="published",
                                    tags=[config.tagsForTumblr], data=file_to_upload)
                break
            except ValueError:
                print("Oops. No internect connection. Upload later.")
                try: #make a text file as a note to upload the .gif later
                    file = open(config.file_path + jpg_group + "-FILENOTUPLOADED.txt", 'w')
                    file.close()
                except:
                    print('Something went wrong. Could not write file.')
                    sys.exit(0) # quit Python
        else: # upload jpgs instead
            try:
                # create an array and populate with file paths to our jpgs
                jpgs = [config.file_path + jpg_group + "-0" + str(i+1) + ".jpg" for i in range(4)]
                client.create_photo(config.tumblr_blog, state="published",
                                    tags=[config.tagsForTumblr], format="markdown",
                                    data=jpgs)
                break
            except ValueError:
                print("Oops. No internect connection. Upload later.")
                try: #make a text file as a note to upload the .gif later
                    file = open(config.file_path + jpg_group + "-FILENOTUPLOADED.txt", 'w')
                    file.close()
                except:
                    print('Something went wrong. Could not write file.')
                    sys.exit(0) # quit Python


def print_photos(jpg_group, img_size):
    conn = cups.Connection()
    printers = conn.getPrinters()
    print('Printers: ' + str(list(printers)))
    cups.setUser('pi')
    if config.print_to_pdf or len(printers) == 1:
        print('Printing to PDF')
        if 'PDF' in printers.keys():
            printer_name = 'PDF'
        else:
            print('No PDF driver.')
            return
    else:
        # TODO: get printer name from config and make sure it's valid
        try:
            printer_name = config.printer_name
            if not printer_name in printers.keys():
                print('Cannot find printer (' + printer_name + ')')
                return
        except AttributeError:
            printer_name = None
            for key in printers.keys():
                if key != 'PDF':
                    printer_name = key
                    break
            if printer_name is None:
                print('no valid printer found')
                return
    img = create_collage(jpg_group, img_size)
    filename = config.file_path + jpg_group + '-collage.jpg'
    pygame.image.save(img, filename)
    print('Printing image')
    conn.printFile(printer_name, filename, 'Photobooth-' + jpg_group, {'fit-to-page':'true'})
        
# define the photo taking function for when the big button is pressed
def start_photobooth():
    try:
        camera = init_camera()

        display_instructions()

        #get the current date and time for the start of the filename
        now = time.strftime("%Y-%m-%d-%H-%M-%S")

        take_pictures(camera, now)

        if config.make_gifs: # make the gifs
            create_gif(now)

        if config.post_online: # turn off posting pics online in config.py
            upload_photo(now)

        display_pics(now)

        # TODO: disable if cups server isn't found
        if config.print_photos:
            print_photos(now, camera.resolution)

    except Exception as e:
        tb = sys.exc_info()[2]
        traceback.print_exception(e.__class__, e, tb)
        pygame.quit()
        sys.exit()
    finally:
        camera.close()

    print("Done")

    if config.post_online:
        show_image(REAL_PATH + "/finished.png")
    else:
        show_image(REAL_PATH + "/finished2.png")

    time.sleep(RESTART_DELAY)
    show_image(REAL_PATH + "/intro.png")
    turn_on_led()


######################
### Initialization ###
######################


# GPIO setup
GPIO.setmode(GPIO.BOARD)
GPIO.setup(LED_PIN, GPIO.OUT) # LED
GPIO.setup(BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
turn_off_led()

# initialize pygame
pygame.init()
SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption('Photo Booth Pics')
pygame.mouse.set_visible(False) #hide the mouse cursor

# Custom event for hardware button press
BUTTON_PRESS_EVENT = pygame.event.Event(pygame.USEREVENT, attr1='ButtonPress')


## clear the previously stored pics based on config settings
if config.clear_on_startup:
    clear_pics()

GPIO.add_event_detect(BTN_PIN, GPIO.RISING, callback=post_button_event, bouncetime=config.debounce)

print("Photo booth app running...")
if not config.have_monitor:
    blink_led(5)


####################
### Main Program ###
####################

show_image(REAL_PATH + "/intro.png")

while True:
    turn_on_led() #turn on the light showing users they can push the button
    for event in pygame.event.get():  # Hit the ESC key to quit the slideshow.
        if (event.type == QUIT or
                (event.type == KEYDOWN and event.key == K_ESCAPE)):
            pygame.quit()
            sys.exit()
        if event.type == pygame.MOUSEBUTTONUP or event == BUTTON_PRESS_EVENT:
            start_photobooth()
            # clear events from when the photobooth was running
            pygame.event.clear()
