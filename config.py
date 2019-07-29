# Tumblr Setup
# Replace the values with your information
# OAuth keys can be generated from https://api.tumblr.com/console/calls/user/info
consumer_key='CONSUMER_KEY' #replace with your key
consumer_secret='CONSUMER_SECRET' #replace with your secret code
oath_token='OATH_TOKEN' #replace with your oath token
oath_secret='OATH_SECRET' #replace with your oath secret code
tumblr_blog = 'TUMBLR_BLOG' # replace with your tumblr account name without .tumblr.com
tagsForTumblr = "MyTagsHere" # change to tags you want, separated with commas

#Config settings to change behavior of photo booth
have_monitor = True # Set to false to enable cues if you have no display
file_path = '/home/pi/Pictures/Photobooth/' # path to save images
clear_on_startup = False # True will clear previously stored photos as the program launches. False will leave all previous photos.
debounce = 200 # how long to debounce the button. Add more time if the button triggers too many times.
post_online = False # True to upload images. False to store locally only.
print_photos = True # Obvious
print_to_pdf = True # Whether to print to a PDF instead of a printer
make_gifs = False   # True to make an animated gif. False to post 4 jpgs into one post.
hi_res_pics = True  # True to save high res pics from camera.
                    # If also uploading, the program will also convert each image to a smaller image before making the gif.
                    # False to first capture low res pics. False is faster.
                    # Careful, each photo costs against your daily Tumblr upload max.
camera_iso = 800    # adjust for lighting issues. Normal is 100 or 200. Sort of dark is 400. Dark is 800 max.
                    # available options: 100, 200, 320, 400, 500, 640, 800
black_and_white = False # Set to True to capture in black and white
