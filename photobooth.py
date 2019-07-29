"""This module simulates a photobooth. See instructions at http://www.drumminhands.com/2014/06/15/raspberry-pi-photo-booth/"""
# created by chris@drumminhands.com
# modified by sproctor@gmail.com

import atexit
import glob
import os
import sys
import socket
import time
import traceback
import RPi.GPIO as GPIO
import picamera # http://picamera.readthedocs.org/en/release-1.4/install2.html
import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE
import pytumblr # https://github.com/tumblr/pytumblr
import config # this is the config python file config.py

########################
### Variables Config ###
########################
led_pin = 7 # LED
btn_pin = 18 # pin for the start button

total_pics = 4 # number of pics to be taken
capture_delay = 1 # delay between pics
prep_delay = 5 # number of seconds at step 1 as users prep to have photo taken
gif_delay = 100 # How much time between frames in the animated gif
restart_delay = 10 # how long to display finished message before beginning a new session
test_server = 'www.google.com'

# full frame of v1 camera is 2592x1944. Wide screen max is 2592,1555
# if you run into resource issues, try smaller, like 1920x1152.
# or increase memory http://picamera.readthedocs.io/en/release-1.12/fov.html#hardware-limits
high_res_w = 1296 # width of high res image, if taken
high_res_h = 972 # height of high res image, if taken

#############################
### Variables that Change ###
#############################
# Do not change these variables, as the code will change it anyway
transform_x = config.monitor_w # how wide to scale the jpg when replaying
transfrom_y = config.monitor_h # how high to scale the jpg when replaying
offset_x = 0 # how far off to left corner to display photos
offset_y = 0 # how far off to left corner to display photos
replay_delay = 1 # how much to wait in-between showing pics on-screen after taking
replay_cycles = 2 # how many times to show each photo on-screen after taking

####################
### Other Config ###
####################
real_path = os.path.dirname(os.path.realpath(__file__))

# Setup the tumblr OAuth Client
client = pytumblr.TumblrRestClient(
    config.consumer_key,
    config.consumer_secret,
    config.oath_token,
    config.oath_secret,
)

# GPIO setup
GPIO.setmode(GPIO.BOARD)
GPIO.setup(led_pin, GPIO.OUT) # LED
GPIO.setup(btn_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.output(led_pin, False) #for some reason the pin turns on at the beginning of the program. Why?

# initialize pygame
pygame.init()
pygame.display.set_mode((config.monitor_w, config.monitor_h))
screen = pygame.display.get_surface()
pygame.display.set_caption('Photo Booth Pics')
pygame.mouse.set_visible(False) #hide the mouse cursor
pygame.display.toggle_fullscreen()

#################
### Functions ###
#################

# clean up running programs as needed when main program exits
def cleanup():
    print('Ended abruptly')
    pygame.quit()
    GPIO.cleanup()


atexit.register(cleanup)


# A function to handle keyboard/mouse/device input events
def input(events):
    for event in events:  # Hit the ESC key to quit the slideshow.
        if (event.type == QUIT or
                (event.type == KEYDOWN and event.key == K_ESCAPE)):
            pygame.quit()


def turn_on_led():
    GPIO.output(led_pin, True)


def turn_off_led():
    GPIO.output(led_pin, False)


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
    blink_led(3)


# check if connected to the internet
def is_connected():
    try:
        # see if we can resolve the host name -- tells us if there is a DNS listening
        host = socket.gethostbyname(test_server)
        # connect to the host -- tells us if the host is actually
        # reachable
        socket.create_connection((host, 80), 2)
        return True
    except:
        pass
    return False


# set variables to properly display the image on screen at right ratio
def set_demensions(img_w, img_h):
    # Note this only works when in booting in desktop mode.
    # When running in terminal, the size is not correct (it displays small). Why?

    # connect to global vars
    global transform_y, transform_x, offset_y, offset_x

    # based on output screen resolution, calculate how to display
    ratio_h = (config.monitor_w * img_h) / img_w

    if ratio_h < config.monitor_h:
        #Use horizontal black bars
        #print "horizontal black bars"
        transform_y = ratio_h
        transform_x = config.monitor_w
        offset_y = (config.monitor_h - ratio_h) / 2
        offset_x = 0
    elif ratio_h > config.monitor_h:
        #Use vertical black bars
        #print "vertical black bars"
        transform_x = (config.monitor_h * img_w) / img_h
        transform_y = config.monitor_h
        offset_x = (config.monitor_w - transform_x) / 2
        offset_y = 0
    else:
        #No need for black bars as photo ratio equals screen ratio
        #print "no black bars"
        transform_x = config.monitor_w
        transform_y = config.monitor_h
        offset_y = offset_x = 0

    # uncomment these lines to troubleshoot screen ratios
#     print str(img_w) + " x " + str(img_h)
#     print "ratio_h: "+ str(ratio_h)
#     print "transform_x: "+ str(transform_x)
#     print "transform_y: "+ str(transform_y)
#     print "offset_y: "+ str(offset_y)
#     print "offset_x: "+ str(offset_x)


# display one image on screen
def show_image(image_path):
    # clear the screen
    screen.fill((0, 0, 0))

    # load the image
    img = pygame.image.load(image_path)
    img = img.convert()

    # set pixel dimensions based on image
    set_demensions(img.get_width(), img.get_height())

    # rescale the image to fit the current display
    img = pygame.transform.scale(img, (transform_x, transfrom_y))
    screen.blit(img, (offset_x, offset_y))
    pygame.display.flip()

# display a blank screen
def clear_screen():
    screen.fill((0, 0, 0))
    pygame.display.flip()

# display a group of images
def display_pics(jpg_group):
    for _ in range(0, replay_cycles): #show pics a few times
        for i in range(1, total_pics + 1): #show each pic
            show_image(config.file_path + jpg_group + "-0" + str(i) + ".jpg")
            time.sleep(replay_delay) # pause

# define the photo taking function for when the big button is pressed
def start_photobooth():

    input(pygame.event.get()) # press escape to exit pygame. Then press ctrl-c to exit python.

    ################################# Begin Step 1 #################################

    print("Get Ready")
    GPIO.output(led_pin, False)
    show_image(real_path + "/instructions.png")
    time.sleep(prep_delay)

    # clear the screen
    clear_screen()

    camera = picamera.PiCamera()
    camera.vflip = False
    camera.hflip = True # flip for preview, showing users a mirror image
    camera.saturation = -100 # comment out this line if you want color images
    camera.iso = config.camera_iso

    pixel_width = 0 # local variable declaration
    pixel_height = 0 # local variable declaration

    if config.hi_res_pics:
        camera.resolution = (high_res_w, high_res_h) # set camera resolution to high res
    else:
        pixel_width = 500 # maximum width of animated gif on tumblr
        pixel_height = config.monitor_h * pixel_width // config.monitor_w
        camera.resolution = (pixel_width, pixel_height) # set camera resolution to low res

    ################################# Begin Step 2 #################################

    print("Taking pics")

    #get the current date and time for the start of the filename
    now = time.strftime("%Y-%m-%d-%H-%M-%S")

    if config.capture_count_pics:
        try: # take the photos
            for i in range(1, total_pics + 1):
                camera.hflip = True # preview a mirror image
                # start preview at low res but the right ratio
                camera.start_preview(resolution=(config.monitor_w, config.monitor_h))
                time.sleep(2) #warm up camera
                turn_on_led()
                filename = config.file_path + now + '-0' + str(i) + '.jpg'
                camera.hflip = False # flip back when taking photo
                camera.capture(filename)
                print(filename)
                turn_off_led()
                camera.stop_preview()
                show_image(real_path + "/pose" + str(i) + ".png")
                time.sleep(capture_delay) # pause in-between shots
                clear_screen()
                if i == total_pics+1:
                    break
        finally:
            camera.close()
    else:
        # start preview at low res but the right ratio
        camera.start_preview(resolution=(config.monitor_w, config.monitor_h))
        time.sleep(2) #warm up camera
        
        try: #take the photos
            for i, filename in enumerate(camera.capture_continuous(config.file_path + now + '-' + '{counter:02d}.jpg')):
                turn_on_led()
                print(filename)
                time.sleep(capture_delay) # pause in-between shots
                turn_off_led()
                if i == total_pics-1:
                    break
        finally:
            camera.stop_preview()
            camera.close()

    ########################### Begin Step 3 #################################

    input(pygame.event.get()) # press escape to exit pygame. Then press ctrl-c to exit python.

    if config.make_gifs: # make the gifs
        print("Creating an animated gif")
        show_image(real_path + "/processing.png")
        if config.hi_res_pics:
            # first make a small version of each image. Tumblr's max animated gif's are 500 pixels wide.
            for x in range(1, total_pics+1): #batch process all the images
                graphicsmagick = "gm convert -size 500x500 " + config.file_path + now + "-0" + str(x) + ".jpg -thumbnail 500x500 " + config.file_path + now + "-0" + str(x) + "-sm.jpg"
                os.system(graphicsmagick) #do the graphicsmagick action

            graphicsmagick = "gm convert -delay " + str(gif_delay) + " " + config.file_path + now + "*-sm.jpg " + config.file_path + now + ".gif" 
            os.system(graphicsmagick) #make the .gif
        else:
            # make an animated gif with the low resolution images
            graphicsmagick = "gm convert -delay " + str(gif_delay) + " " + config.file_path + now + "*.jpg " + config.file_path + now + ".gif" 
            os.system(graphicsmagick) #make the .gif

    if config.post_online: # turn off posting pics online in config.py
        show_image(real_path + "/uploading.png")
        connected = is_connected() #check to see if you have an internet connection

        if (connected == False):
            print("bad internet connection")
         
        while connected:
            if config.make_gifs: 
                try:
                    file_to_upload = config.file_path + now + ".gif"
                    client.create_photo(config.tumblr_blog, state="published", tags=[config.tagsForTumblr], data=file_to_upload)
                    break
                except ValueError:
                    print("Oops. No internect connection. Upload later.")
                    try: #make a text file as a note to upload the .gif later
                        file = open(config.file_path + now + "-FILENOTUPLOADED.txt",'w')   # Trying to create a new file or open one
                        file.close()
                    except:
                        print('Something went wrong. Could not write file.')
                        sys.exit(0) # quit Python
            else: # upload jpgs instead
                try:
                    # create an array and populate with file paths to our jpgs
                    my_jpgs = [config.file_path + now + "-0" + str(i+1) + ".jpg" for i in range(4)]
                    client.create_photo(config.tumblr_blog, state="published", tags=[config.tagsForTumblr], format="markdown", data=my_jpgs)
                    break
                except ValueError:
                    print("Oops. No internect connection. Upload later.")
                    try: #make a text file as a note to upload the .gif later
                        file = open(config.file_path + now + "-FILENOTUPLOADED.txt", 'w')   # Trying to create a new file or open one
                        file.close()
                    except:
                        print('Something went wrong. Could not write file.')
                        sys.exit(0) # quit Python
    
    ########################### Begin Step 4 #################################
    
    input(pygame.event.get()) # press escape to exit pygame. Then press ctrl-c to exit python.
    
    try:
        display_pics(now)
    except Exception as e:
        tb = sys.exc_info()[2]
        traceback.print_exception(e.__class__, e, tb)
        pygame.quit()
        
    print("Done")
    
    if config.post_online:
        show_image(real_path + "/finished.png")
    else:
        show_image(real_path + "/finished2.png")
    
    time.sleep(restart_delay)
    show_image(real_path + "/intro.png")
    turn_on_led()


####################
### Main Program ###
####################

## clear the previously stored pics based on config settings
if config.clear_on_startup:
    clear_pics()

print("Photo booth app running...")
blink_led(5)

show_image(real_path + "/intro.png")

while True:
    turn_on_led() #turn on the light showing users they can push the button
    input(pygame.event.get()) # press escape to exit pygame.
    if not GPIO.wait_for_edge(btn_pin, GPIO.FALLING, timeout=100, bouncetime=config.debounce) is None:
        start_photobooth()
