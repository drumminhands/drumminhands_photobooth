# This module simulates a photobooth.
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
import pygame.freetype
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE

import config # this is the config python file config.py

########################
### Variables Config ###
########################
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


#delete files in folder
def clear_pics():
    files = glob.glob(config.file_path + '*')
    for f in files:
        os.remove(f)
    #light the lights in series to show completed
    print("Deleted previous pics")


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


def blit_text(surface, pos, text, font, fgcolor=None, width=None):
    font.origin = True
    lines = [line.split(' ') for line in text.splitlines()]  # 2D array where each row is a list of words.
    line_spacing = font.get_sized_height() + 2
    space = font.get_rect(' ')
    height = surface.get_height()
    if width is None:
        width = surface.get_width()
    x, y = pos
    for words in lines:
        for word in words:
            bounds = font.get_rect(word)
            if x + bounds.width + bounds.x >= width:
                x, y = pos[0] + 4 * space.width, y + line_spacing
            if x + bounds.width + bounds.x >= width:
                raise ValueError("word too wide for the surface")
            if y + bounds.height - bounds.y >= height:
                raise ValueError("text to long for the surface")
            font.render_to(surface, (x, y), None, fgcolor)
            x += bounds.width + space.width
        x, y = pos[0], y + line_spacing # new line


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
    if config.black_and_white:
        camera.saturation = -100
    if config.camera_iso:
        camera.iso = config.camera_iso
    return camera


def display_instructions():
    print("Displaying instructions")
    show_image(REAL_PATH + "/instructions.png")
    time.sleep(PREP_DELAY)


def display_intro():
    SCREEN.fill((0, 0, 0))
    title_font = pygame.freetype.SysFont('DejaVu Sans', 60)
    title_size_rect = title_font.get_rect('Instructions')
    title_x = (SCREEN.get_width() - title_size_rect.width) // 2
    title_rect = title_font.render_to(SCREEN, (title_x, 4), None, (255, 255, 255))
    text_top = title_rect.bottom + 8
    text_font = pygame.freetype.SysFont('DejaVu Sans', 28)
    english_text = """1. Make sure the lights are ON
2. Choose your costume
3. Tap this screen
4. Pose for 4 pictures
5. Wait for the picture to print
6. Put the picture in the guestbook with your message"""
    french_text = """1. Verifier que les lumieres sont allumees
2. Choisir votre deguisement
3. Toucher l'ecran
4. Prenez la pose pour 4 photos
5. Attendre que les photos s'impriment
6. Coller la photo dans le livre d'or avec votre petit mot"""
    blit_text(SCREEN, (4, text_top), english_text, text_font, (255, 255, 255), SCREEN.get_width() // 2 - 8)
    blit_text(SCREEN, (SCREEN.get_width() // 2 + 4, text_top), french_text, text_font, (255, 255, 255), SCREEN.get_width() - 4)
    pygame.display.flip()
    #show_image(REAL_PATH + "/intro.png")


def take_pictures(camera, jpg_group):
    print("Taking pics")

    camera.annotate_text_size = 160
    camera.annotate_foreground = picamera.Color('black')

    for i in range(1, TOTAL_PICS + 1):
        camera.hflip = True # preview a mirror image
        camera.start_preview()
        for n in range(CAPTURE_DELAY, 0, -1):
            surface = pygame.Surface(SCREEN.get_size(), pygame.SRCALPHA)
            font = pygame.freetype.SysFont('DejaVu Sans', 360)
            rect = font.get_rect(str(n))
            pos = (surface.get_width() - rect.width) // 2, (surface.get_height() - rect.height) // 2
            font.render_to(surface, pos, None, (0, 0, 0))
            overlay = camera.add_overlay(pygame.image.tostring(surface, 'RGBA'), surface.get_size(), layer=3, format='rgba')
            time.sleep(0.5)
            camera.remove_overlay(overlay)
            time.sleep(0.5)
        # Make the screen white
        SCREEN.fill((255, 255, 255))
        pygame.display.flip()
        camera.stop_preview()
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
    print('Printing to ' + printer_name)
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


######################
### Initialization ###
######################


# GPIO setup
GPIO.setmode(GPIO.BOARD)
GPIO.setup(BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

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

GPIO.add_event_detect(BTN_PIN, GPIO.RISING, callback=post_button_event, bouncetime=200)

print("Photo booth app running...")


####################
### Main Program ###
####################

while True:
    display_intro()

    for event in pygame.event.get():  # Hit the ESC key to quit the slideshow.
        if (event.type == QUIT or
                (event.type == KEYDOWN and event.key == K_ESCAPE)):
            pygame.quit()
            sys.exit()
        if event.type == pygame.MOUSEBUTTONUP or event == BUTTON_PRESS_EVENT:
            start_photobooth()
            # clear events from when the photobooth was running
            pygame.event.clear()
