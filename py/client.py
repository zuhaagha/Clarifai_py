import base64, json, os, urllib2, urllib

from PIL import Image
from cStringIO import StringIO
from mime_util import post_images_multipart

class ApiError(Exception):
  """Api error."""
  pass


############################
# Enter your ID and SECRET for a Clarifai API Application.
CLIENT_ID = 'OPoiUWRqHGOmcKjkFmHHLVecwsyt_hbogTlHmKsb'
CLIENT_SECRET = '-MXxNPtRjnPwM7KN69mqQtaDfbF2vodyXcuQcJiSBeWcfpPno5WtJ7jttBDcTXIMwDVAY2S_cP6Bhid8s9cWZyQda-eLXWhJB5TSfHpaLHUtxmV5Abq-csbxmD5gEjVU'


# # api.clarifai.com prod
# CLIENT_ID = 'j57To4jogXszzcRHsruVyUQiYSybh_lhfVP6cvAS'
# CLIENT_SECRET = 'jEnNVzsLTQKEBstmF2onqBBEV6L2SSHW49fRgs2aMOZ7neQ9kqw1IqkA0rxP2Sb3-Bepjloy_kX9uOM6TV37gOtMplQznlUAXaay9_k2mvoA-aevZl-N2gBwXusMecXl'

############################

# cl.tag_image_url(['http://www.clarifai.com/img/metro-north.jpg' for j in range(100)])


############################
# Clarifai Parameters. DO NOT TOUCH
SUPPORTED_OPS = ['tag','embed','tag,embed']

MIN_SIZE = 256
MAX_SIZE = 512
IM_QUALITY = 95
API_VERSION = 'v1'

class ClarifaiApi(object):
  def __init__(self, base_url='http://api.clarifai.com'):
    self._base_url = base_url
    self._urls = {
      'tag': os.path.join(self._base_url, '%s/tag/' % API_VERSION),
      'embed': os.path.join(self._base_url, '%s/embed/' % API_VERSION),
      'tag,embed': os.path.join(self._base_url, '%s/multiop/' % API_VERSION),
      'token': os.path.join(self._base_url, '%s/token/' % API_VERSION),
      'info': os.path.join(self._base_url, '%s/info/' % API_VERSION),
      }
    self.access_token = None

  def get_access_token(self):
    headers = {}  # don't use json here, juse urlencode.
    url = self._url_for_op('token')
    data = {'grant_type': 'client_credentials',
            'client_id':CLIENT_ID,
            'client_secret':CLIENT_SECRET}
    response = self._get_response(url, data, headers)
    response = json.loads(response)
    self.access_token = response['access_token']
    return response

  def get_info(self):
    url = self._url_for_op('info')
    headers = self._get_json_headers()
    data = {'blah':'blah'}
    data= None
    # Should do get now.
    response = self._get_response(url, data, headers)
    response = json.loads(response)
    return response

  def _url_for_op(self, op):
    return self._urls.get(op)

  def tag_image(self, image_files):
    """ Autotag a single image from an open file object or multiples images from a list of open file
    objects.

    The only method used on the file object is read() to get the bytes of the compressed
    image representation.

    Args:
      image_files: a single (file, name) tuple or a list of (file, name) tuples, where file is an
      open file-like object containing the encoded image bytes.

    Returns:
      results: a tuple of (tag, probability) if a single image is processed or a list of (tag,
      probability) tuples if multiple images are processed.

    Example:
      from api.py.client import ClarifaiApi
      clarifai_api = ClarifaiApi()
      clarifai_api.tag_images([open('/path/to/local/image.jpeg'),
                               open('/path/to/local/image2.jpeg')])
    """
    return self._multi_image_op(image_files, 'tag')

  def embed_image(self, image_files):
    """ Embed a single image from an open file object or multiples images from a list of open file
    objects.

    The only method used on the file object is read() to get the bytes of the compressed
    image representation.

    Args:
      image_files: a single (file, name) tuple or a list of (file, name) tuples, where file is an
      open file-like object containing the encoded image bytes.

    Returns:
      results: a tuple of (tag, probability) if a single image is processed or a list of (tag,
      probability) tuples if multiple images are processed.

    Example:
      from api.py.client import ClarifaiApi
      clarifai_api = ClarifaiApi()
      clarifai_api.tag_images([open('/path/to/local/image.jpeg'),
                               open('/path/to/local/image2.jpeg')])
    """
    return self._multi_image_op(image_files, 'embed')

  def tag_and_embed_image(self, image_files):
    return self._multi_image_op(image_files, 'tag,embed')

  def tag_image_url(self, image_urls):
    """ Tag an image from a url or images from a list of urls.
      image_urls: a single url for the input image to be processed or a list of urls for a set of
      images to be processed.

    Returns:
      results: a (tag, probability) tuple if a single image was used, or a list of (tag,
      probability) tuples when multiple images are input.

    Example:
      from api.py.client import ClarifaiApi
      clarifai_api = ClarifaiApi()
      clarifai_api.tag_image_url(['http://www.clarifai.com/img/metro-north.jpg',
                                  'http://www.clarifai.com/img/metro-north.jpg'])

    """
    return self._multi_imageurl_op(image_urls, 'tag')

  def embed_image_url(self, image_urls):
    """ Embed an image from a url or images from a list of urls.

    Args:
      image_urls: a single url for the input image to be processed or a list of urls for a set of
    images to be processed.

    Returns:

    """
    return self._multi_imageurl_op(image_urls, 'embed')

  def tag_and_embed_image_url(self, image_urls):
    """ Take in a list of image urls, downloading them on the server side and returning both
    classifications and embeddings.

    Args:
      image_urls: a single url for the input image to be processed or a list of urls for a set of
    images to be processed.

    Returns:

    """
    return self._multi_imageurl_op(image_urls, 'tag,embed')

  def _resize_image_tuple(self, image_tup):
    """ Resize the (image, name) so that it falls between MIN_SIZE and MAX_SIZE as the minimum
    dimension.
    """
    try:
      img = Image.open(image_tup[0])
      ms = min(img.size)
      min_ratio = float(MIN_SIZE) / ms
      max_ratio = float(MAX_SIZE) / ms
      def get_newsize(img, ratio, SIZE):
        if img.size[0] == ms:
          newsize = (SIZE, int(round(ratio * img.size[1])))
        else:
          newsize = (int(round(ratio * img.size[0])), SIZE)
        return newsize
      im_changed = False
      # Only resample if min size is > 512 or < 256
      if max_ratio < 1.0:  # downsample to MAX_SIZE
        newsize = get_newsize(img, max_ratio, MAX_SIZE)
        img = img.resize(newsize, Image.BILINEAR)
        im_changed = True
      elif min_ratio > 1.0:  # upsample to MIN_SIZE
        newsize = get_newsize(img, min_ratio, MIN_SIZE)
        img = img.resize(newsize, Image.BICUBIC)
        im_changed = True
      else:  # no changes needed so rewind file-object.
        image_tup[0].seek(0)
      # Finally make sure we have RGB images.
      if img.mode != "RGB":
        img = img.convert("RGB")
        im_changed = True
      if im_changed:
        io = StringIO()
        img.save(io, 'jpeg', quality=IM_QUALITY)
        io.seek(0)  # rewind file-object to read() below is good to go.
        image_tup = (io, image_tup[1])
    except IOError, e:
      print "Could not open image file: %s, still sending to server." % image_tup[1]
    return image_tup

  def _process_image_files(self, image_files):
    # Handle single file-object as arg.
    if not isinstance(image_files, list):
      image_files = [image_files]
    # Handle unnames images as lists of file objects. Named by index in list.
    for i, tup in enumerate(image_files):
      if not isinstance(tup, tuple):
        image_files[i] = (tup, str(i))
        assert hasattr(image_files[i][0], 'read'), (
            'image_files[%d] has wrong type: %s. Must be file-object with read method.') % (
                i, type(image_files[i][0]))
    # Resize any images such that the
    for i, image_tup in enumerate(image_files):
      image_files[i] = self._resize_image_tuple(image_tup)
    # Return a list of (bytes, name) tuples of the encoded image bytes.
    image_data = []
    for image_file in image_files:
      image_data.append((bytes(image_file[0].read()), image_file[1]))
    return image_data

  def _multi_image_op(self, image_files, op):
    ''' Supports both list of tuples (image_file, name) or a list of image_files where a name will
    be created as the index into the list. '''
    if op not in SUPPORTED_OPS:
      raise Exception('Unsupported op: %s, ops available: %s' % (op, str(SUPPORTED_OPS)))
    image_data = self._process_image_files(image_files)
    data = {'op': op}
    url = self._url_for_op(op)
    if self.access_token is None:
      self.get_access_token()
    response = post_images_multipart(image_data, data, url, self.access_token)
    return self._parse_response(response, op)

  def _multi_imageurl_op(self, image_urls, op):
    ''' If sending image_url or image_file strings, then we can send as json directly instead of the
    multipart form. '''
    if op not in SUPPORTED_OPS:
      raise Exception('Unsupported op: %s, ops available: %s' % (op, str(SUPPORTED_OPS)))
    if not isinstance(image_urls, list):
      image_urls = [image_urls]
    if not isinstance(image_urls[0], basestring):
      raise Exception("image_urls must be strings")
    data =  {'op':op,
             'url': image_urls}
    headers = self._get_json_headers()
    url = self._url_for_op(data['op'])
    response = self._get_response(url, data, headers)
    return self._parse_response(response, op)

  def _parse_response(self, response, all_ops):
    try:
      response = json.loads(response)
    except ValueError as e:
      raise ApiError(e)
    if 'error' in response:
      raise ApiError(response['error'])
    # Return the true API return value.
    return response
    # results = {}
    # for op in all_ops.split(','):
    #   op_results = []
    #   if op == 'tag':
    #     num_imgs = len(response[op]['predictions']['classes'])
    #     for i in range(num_imgs):
    #       op_results.append(
    #           zip(response[op]['predictions']['classes'][i],
    #               response[op]['predictions']['probs'][i]))
    #   elif op == 'extract':
    #     op_results = response[op]['features']
    #   elif op == 'embed':
    #     op_results = response[op]['embeddings']
    #   # If single image, we just return the results, no list.
    #   if len(op_results) == 1: # single image query
    #     results[op] = op_results[0]  # return directly
    #   else:
    #     results[op] = op_results  # return as list.
    # # If single op, we just return the results, no dict.
    # if len(results) == 1:
    #   return results.values()[0]
    # return results

  def _get_json_headers(self):
    if self.access_token is None:
      self.get_access_token()
    headers = {"content-type": "application/json",
               "Authorization": "Bearer %s" % self.access_token}
    return headers

  def _get_response(self, url, data, headers):
    if data:
      if headers.get("content-type","") == "application/json":
        data = json.dumps(data)
      else:
        data = urllib.urlencode(data)
    req = urllib2.Request(url, data, headers)
    try:
      response = urllib2.urlopen(req)
      raw_response = response.read()
    except urllib2.HTTPError as e:
      raise ApiError(e.read())
    return raw_response


  def old_tag_image(self, image_files):
    """ DEPRECATED: use tag_images which is more efficient and support single or multiple images.

    Autotag an image.

    Args:
      image_file: an open file-like object containing the encodeed image bytes. The read
      method is called on this object to get the encoded bytes so it can be a file handle or
      StringIO buffer.

    Returns:
      results: A list of (tag, probability) tuples.

    Example:
      clarifai_api = ClarifaiApi()
      clarifai_api.tag_image(open('/path/to/local/image.jpeg'))
    """
    data = {'encoded_image': base64.encodestring(image_files[0].read())}
    return self._single_image_op(data, 'tag')


  def _single_image_op(self, data, op):
    """ DEPRECATED: use _multi_image_op which is more efficient.
    """
    if op not in SUPPORTED_OPS:
      raise Exception('Unsupported op: %s, ops available: %s' % (op, str(SUPPORTED_OPS)))
    data['op'] =  op
    headers = self._get_json_headers()
    url = self._url_for_op(data['op'])
    response = self._get_response(url, data, headers)
    return dict([(k, v[0]) for k, v in self._parse_response(response, op).items()])
