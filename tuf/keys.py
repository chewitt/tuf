"""
<Program Name>
  keys.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  October 4, 2013.

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  The goal of this module is to support public-key cryptography using the RSA
  algorithm.  The RSA-related functions provided include generate(),
  create_signature(), and verify_signature().  The create_encrypted_pem() and
  create_from_encrypted_pem() functions are optional, and may be used save a
  generated RSA key to a file.  The 'PyCrypto' package used by 'rsa_key.py'
  generates the actual RSA keys and the functions listed above can be viewed
  as an easy-to-use public interface.  Additional functions contained here
  include create_in_metadata_format() and create_from_metadata_format().  These
  last two functions produce or use RSA keys compatible with the key structures
  listed in TUF Metadata files.  The generate() function returns a dictionary
  containing all the information needed of RSA keys, such as public and private=
  keys, keyIDs, and an idenfier.  create_signature() and verify_signature() are
  supplemental functions used for generating RSA signatures and verifying them.
  https://en.wikipedia.org/wiki/RSA_(algorithm)

  Key IDs are used as identifiers for keys (e.g., RSA key).  They are the
  hexadecimal representation of the hash of key object (specifically, the key
  object containing only the public key).  Review 'rsa_key.py' and the
  '_get_keyid()' function to see precisely how keyids are generated.  One may
  get the keyid of a key object by simply accessing the dictionary's 'keyid'
  key (i.e., rsakey['keyid']).
 """

# Required for hexadecimal conversions.  Signatures and public/private keys are
# hexlified.
import binascii

#
_SUPPORTED_RSA_CRYPTO_LIBRARIES = ['pycrypto']

# 
_SUPPORTED_ED25519_CRYPTO_LIBRARIES = ['ed25519', 'pynacl']

# 
_available_crypto_libraries = ['ed25519']

try:
  import Crypto
  import tuf.pycrypto_keys
  _available_crypto_libraries.append('pycrypto')
except ImportError:
  pass

try:
  import nacl
  _available_crypto_libraries.append('pynacl')
except ImportError:
  pass

import tuf.ed25519_keys


import tuf
import tuf.conf

# Digest objects needed to generate hashes.
import tuf.hash

# Perform object format-checking.
import tuf.formats


_KEY_ID_HASH_ALGORITHM = 'sha256'

# Recommended RSA key sizes:
# http://www.emc.com/emc-plus/rsa-labs/historical/twirl-and-rsa-key-size.htm#table1
# According to the document above, revised May 6, 2003, RSA keys of
# size 3072 provide security through 2031 and beyond.
_DEFAULT_RSA_KEY_BITS = 3072

# The crypto libraries used in 'keys.py'.
_RSA_CRYPTO_LIBRARY = tuf.conf.RSA_CRYPTO_LIBRARY
_ED25519_CRYPTO_LIBRARY = tuf.conf.ED25519_CRYPTO_LIBRARY


def generate_rsa_key(bits=_DEFAULT_RSA_KEY_BITS):
  """
  <Purpose> 
    Generate public and private RSA keys, with modulus length 'bits'.
    In addition, a keyid used as an identifier for RSA keys is generated.
    The object returned conforms to 'tuf.formats.RSAKEY_SCHEMA' and as the form:
    {'keytype': 'rsa',
     'keyid': keyid,
     'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                'private': '-----BEGIN RSA PRIVATE KEY----- ...'}}
    
    The public and private keys are in PEM format and stored as strings.

    Although the crytography library called sets a 1024-bit minimum key size,
    generate() enforces a minimum key size of 2048 bits.  If 'bits' is
    unspecified, a 3072-bit RSA key is generated, which is the key size
    recommended by TUF. 
    
    >>> rsa_key = generate_rsa_key(bits=2048)
    >>> tuf.formats.RSAKEY_SCHEMA.matches(rsa_key)
    True
    >>> public = rsa_key['keyval']['public']
    >>> private = rsa_key['keyval']['private']
    >>> tuf.formats.PEMRSA_SCHEMA.matches(public)
    True
    >>> tuf.formats.PEMRSA_SCHEMA.matches(private)
    True
  
  <Arguments>
    bits:
      The key size, or key length, of the RSA key.  'bits' must be 2048, or
      greater, and a multiple of 256.

  <Exceptions>
    ValueError, if an exception occurs after calling the RSA key generation
    routine.  'bits' must be a multiple of 256.  The 'ValueError' exception is
    raised by the key generation function of the cryptography library called.

    tuf.FormatError, if 'bits' does not contain the correct format.

  <Side Effects>
    The RSA keys are generated by calling PyCrypto's
    Crypto.PublicKey.RSA.generate().

  <Returns>
    A dictionary containing the RSA keys and other identifying information.
  """

  # Does 'bits' have the correct format?
  # This check will ensure 'bits' conforms to 'tuf.formats.RSAKEYBITS_SCHEMA'.
  # 'bits' must be an integer object, with a minimum value of 2048.
  # Raise 'tuf.FormatError' if the check fails.
  tuf.formats.RSAKEYBITS_SCHEMA.check_match(bits)

  # Raise 'tuf.Error' if 'tuf.conf.CRYPTO_LIBRARY' is not supported or could
  # not be imported.
  _check_crypto_libraries()

  # Check for valid crypto library
  # Begin building the RSA key dictionary. 
  rsakey_dict = {}
  keytype = 'rsa'
  public = None
  private = None

  # Generate the public and private RSA keys.  The PyCrypto module performs
  # the actual key generation.  Raise 'ValueError' if 'bits' is less than 1024 
  # or not a multiple of 256, although a 2048-bit minimum is enforced by
  # tuf.formats.RSAKEYBITS_SCHEMA.check_match().
  if _RSA_CRYPTO_LIBRARY == 'pycrypto':
    public, private = tuf.pycrypto_keys.generate_rsa_public_and_private(bits)
  else:
    message = 'Invalid crypto library: '+repr(_RSA_CRYPTO_LIBRARY)+'.'
    raise ValueError(message) 
    
  # Generate the keyid for the RSA key.  'key_value' corresponds to the
  # 'keyval' entry of the 'RSAKEY_SCHEMA' dictionary.  The private key
  # information is not included in the generation of the 'keyid' identifier.
  key_value = {'public': public,
               'private': ''}
  keyid = _get_keyid(keytype, key_value)

  # Build the 'rsakey_dict' dictionary.  Update 'key_value' with the RSA
  # private key prior to adding 'key_value' to 'rsakey_dict'.
  key_value['private'] = private

  rsakey_dict['keytype'] = keytype
  rsakey_dict['keyid'] = keyid
  rsakey_dict['keyval'] = key_value

  return rsakey_dict





def generate_ed25519_key():
  """
  <Purpose> 
    Generate public and private RSA keys, with modulus length 'bits'.
    In addition, a keyid used as an identifier for RSA keys is generated.
    The object returned conforms to 'tuf.formats.RSAKEY_SCHEMA' and as the form:
    {'keytype': 'ed25519',
     'keyid': keyid,
     'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                'private': '-----BEGIN RSA PRIVATE KEY----- ...'}}
    
    The public and private keys are in PEM format and stored as strings.

    Although the crytography library called sets a 1024-bit minimum key size,
    generate() enforces a minimum key size of 2048 bits.  If 'bits' is
    unspecified, a 3072-bit RSA key is generated, which is the key size
    recommended by TUF. 
  
    >>> ed25519_key = generate_ed25519_key()
    >>> tuf.formats.ED25519KEY_SCHEMA.matches(ed25519_key)
    True
    >>> len(ed25519_key['keyval']['public'])
    64
    >>> len(ed25519_key['keyval']['private'])
    64

  <Arguments>
    None.
  
  <Exceptions>
    ValueError, if an exception occurs after calling the RSA key generation
    routine.  'bits' must be a multiple of 256.  The 'ValueError' exception is
    raised by the key generation function of the cryptography library called.

    tuf.FormatError, if 'bits' does not contain the correct format.

  <Side Effects>
    The RSA keys are generated by calling PyCrypto's
    Crypto.PublicKey.RSA.generate().

  <Returns>
    A dictionary containing the RSA keys and other identifying information.
  """

  # Raise 'tuf.Error' if 'tuf.conf.CRYPTO_LIBRARY' is not supported or could
  # not be imported.
  _check_crypto_libraries()

  # Check for valid crypto library
  # Begin building the RSA key dictionary. 
  ed25519_key = {}
  keytype = 'ed25519'
  public = None
  private = None

  # Generate the public and private RSA keys.  The PyCrypto module performs
  # the actual key generation.  Raise 'ValueError' if 'bits' is less than 1024 
  # or not a multiple of 256, although a 2048-bit minimum is enforced by
  # tuf.formats.RSAKEYBITS_SCHEMA.check_match().
  if 'pynacl' in _available_crypto_libraries:
    public, private = \
      tuf.ed25519_keys.generate_public_and_private(use_pynacl=True)
  else:
    public, private = \
      tuf.ed25519_keys.generate_public_and_private(use_pynacl=False)
    
  # Generate the keyid for the RSA key.  'key_value' corresponds to the
  # 'keyval' entry of the 'RSAKEY_SCHEMA' dictionary.  The private key
  # information is not included in the generation of the 'keyid' identifier.
  key_value = {'public': binascii.hexlify(public),
               'private': ''}
  keyid = _get_keyid(keytype, key_value)

  # Build the 'rsakey_dict' dictionary.  Update 'key_value' with the RSA
  # private key prior to adding 'key_value' to 'rsakey_dict'.
  key_value['private'] = binascii.hexlify(private)

  ed25519_key['keytype'] = keytype
  ed25519_key['keyid'] = keyid
  ed25519_key['keyval'] = key_value

  return ed25519_key





def create_in_metadata_format(keytype, key_value, private=False):
  """
  <Purpose>
    Return a dictionary conformant to 'tuf.formats.KEY_SCHEMA'.
    If 'private' is True, include the private key.  The dictionary
    returned has the form:
    {'keytype': 'rsa',
     'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                'private': '-----BEGIN RSA PRIVATE KEY----- ...'}}
    
    or if 'private' is False:

    {'keytype': 'rsa',
     'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                'private': ''}}
    
    The private and public keys are in PEM format.
    
    RSA keys are stored in Metadata files (e.g., root.txt) in the format
    returned by this function.
    
    >>> ed25519_key = generate_ed25519_key()
    >>> key_val = ed25519_key['keyval']
    >>> keytype = ed25519_key['keytype']
    >>> ed25519_metadata = \
    create_in_metadata_format(keytype, key_val, private=True)
    >>> tuf.formats.KEY_SCHEMA.matches(ed25519_metadata)
    True
  
  <Arguments>
    key_type:
      'rsa' or 'ed25519'.      

    key_value:
      A dictionary containing a private and public RSA key.
      'key_value' is of the form:

      {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
       'private': '-----BEGIN RSA PRIVATE KEY----- ...'}},
      conformat to 'tuf.formats.KEYVAL_SCHEMA'.

    private:
      Indicates if the private key should be included in the
      returned dictionary.

  <Exceptions>
    tuf.FormatError, if 'key_value' does not conform to 
    'tuf.formats.KEYVAL_SCHEMA'.

  <Side Effects>
    None.

  <Returns>
    An 'KEY_SCHEMA' dictionary.
  """

  # Does 'keytype' have the correct format?
  # This check will ensure 'keytype' has the appropriate number
  # of objects and object types, and that all dict keys are properly named.
  # Raise 'tuf.FormatError' if the check fails.
  tuf.formats.KEYTYPE_SCHEMA.check_match(keytype)
  
  # Does 'key_value' have the correct format?
  tuf.formats.KEYVAL_SCHEMA.check_match(key_value)

  if private is True and key_value['private']:
    return {'keytype': keytype, 'keyval': key_value}
  else:
    public_key_value = {'public': key_value['public'], 'private': ''}
    return {'keytype': keytype, 'keyval': public_key_value}





def create_from_metadata_format(key_metadata):
  """
  <Purpose>
    Construct an RSA key dictionary (i.e., tuf.formats.RSAKEY_SCHEMA)
    from 'key_metadata'.  The dict returned by this function has the exact
    format as the dict returned by generate().  It is of the form:
   
    {'keytype': 'rsa',
     'keyid': keyid,
     'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                'private': '-----BEGIN RSA PRIVATE KEY----- ...'}}

    The public and private keys are in PEM format and stored as strings.

    RSA key dictionaries in RSAKEY_SCHEMA format should be used by
    modules storing a collection of keys, such as a keydb and keystore.
    RSA keys as stored in metadata files use a different format, so this 
    function should be called if an RSA key is extracted from one of these 
    metadata files and needs converting.  Generate() creates an entirely
    new key and returns it in the format appropriate for 'keydb.py' and
    'keystore.py'.
    
    >>> ed25519_key = generate_ed25519_key()
    >>> key_val = ed25519_key['keyval']
    >>> keytype = ed25519_key['keytype']
    >>> ed25519_metadata = \
    create_in_metadata_format(keytype, key_val, private=True)
    >>> ed25519_key_2 = create_from_metadata_format(ed25519_metadata)
    >>> tuf.formats.ED25519KEY_SCHEMA.matches(ed25519_key_2)
    True
    >>> ed25519_key == ed25519_key_2
    True

  <Arguments>
    key_metadata:
      The RSA key dictionary as stored in Metadata files, conforming to
      'tuf.formats.KEY_SCHEMA'.  It has the form:
      
      {'keytype': '...',
       'keyval': {'public': '...',
                  'private': '...'}}

  <Exceptions>
    tuf.FormatError, if 'key_metadata' does not conform to
    'tuf.formats.KEY_SCHEMA'.

  <Side Effects>
    None.

  <Returns>
    A dictionary containing the RSA keys and other identifying information.
  """

  # Does 'key_metadata' have the correct format?
  # This check will ensure 'key_metadata' has the appropriate number
  # of objects and object types, and that all dict keys are properly named.
  # Raise 'tuf.FormatError' if the check fails.
  tuf.formats.KEY_SCHEMA.check_match(key_metadata)

  # Construct the dictionary to be returned.
  key_dict = {}
  keytype = key_metadata['keytype']
  key_value = key_metadata['keyval']

  # Convert 'key_value' to 'tuf.formats.KEY_SCHEMA' and generate its hash
  # The hash is in hexdigest form. 
  keyid = _get_keyid(keytype, key_value)

  # We now have all the required key values.  Build 'rsakey_dict'.
  key_dict['keytype'] = keytype
  key_dict['keyid'] = keyid
  key_dict['keyval'] = key_value

  return key_dict





def _get_keyid(keytype, key_value):
  """Return the keyid for 'key_value'."""

  # 'keyid' will be generated from an object conformant to KEY_SCHEMA,
  # which is the format Metadata files (e.g., root.txt) store keys.
  # 'create_in_metadata_format()' returns the object needed by _get_keyid().
  rsakey_meta = create_in_metadata_format(keytype, key_value, private=False)

  # Convert the RSA key to JSON Canonical format suitable for adding
  # to digest objects.
  rsakey_update_data = tuf.formats.encode_canonical(rsakey_meta)

  # Create a digest object and call update(), using the JSON 
  # canonical format of 'rskey_meta' as the update data.
  digest_object = tuf.hash.digest(_KEY_ID_HASH_ALGORITHM)
  digest_object.update(rsakey_update_data)

  # 'keyid' becomes the hexadecimal representation of the hash.  
  keyid = digest_object.hexdigest()

  return keyid





def _check_crypto_libraries():
  """ check """
  
  if _RSA_CRYPTO_LIBRARY not in _SUPPORTED_RSA_CRYPTO_LIBRARIES:
    message = 'The '+repr(_RSA_CRYPTO_LIBRARY)+' crypto library specified'+ \
      ' in "tuf.conf.RSA_CRYPTO_LIBRARY" is not supported.\n'+ \
      'Supported crypto libraries: '+repr(_SUPPORTED_RSA_CRYPTO_LIBRARIES)+'.'
    raise tuf.CryptoError(message)
  
  if _ED25519_CRYPTO_LIBRARY not in _SUPPORTED_ED25519_CRYPTO_LIBRARIES:
    message = 'The '+repr(_ED25519_CRYPTO_LIBRARY)+' crypto library specified'+ \
      ' in "tuf.conf.ED25519_CRYPTO_LIBRARY" is not supported.\n'+ \
      'Supported crypto libraries: '+repr(_SUPPORTED_ED25519_CRYPTO_LIBRARIES)+'.'
    raise tuf.CryptoError(message)

  if _RSA_CRYPTO_LIBRARY not in _available_crypto_libraries:
    message = 'The '+repr(_RSA_CRYPTO_LIBRARY)+' crypto library specified'+ \
      ' in "tuf.conf.RSA_CRYPTO_LIBRARY" could not be imported.'
    raise tuf.CryptoError(message)
  
  if _ED25519_CRYPTO_LIBRARY not in _available_crypto_libraries:
    message = 'The '+repr(_ED25519_CRYPTO_LIBRARY)+' crypto library specified'+ \
      ' in "tuf.conf.ED25519_CRYPTO_LIBRARY" could not be imported.'
    raise tuf.CryptoError(message)





def create_signature(key_dict, data):
  """
  <Purpose>
    Return a signature dictionary of the form:
    {'keyid': keyid,
     'method': 'PyCrypto-PKCS#1 PPS',
     'sig': sig}.

    The signing process will use the private key
    rsakey_dict['keyval']['private'] and 'data' to generate the signature.

    RFC3447 - RSASSA-PSS 
    http://www.ietf.org/rfc/rfc3447.
    
    >>> ed25519_key = generate_ed25519_key()
    >>> data = 'The quick brown fox jumps over the lazy dog'
    >>> signature = create_signature(ed25519_key, data)
    >>> tuf.formats.SIGNATURE_SCHEMA.matches(signature)
    True
    >>> len(signature['sig'])
    128
    >>> rsa_key = generate_rsa_key(2048)
    >>> data = 'The quick brown fox jumps over the lazy dog'
    >>> signature = create_signature(rsa_key, data)
    >>> tuf.formats.SIGNATURE_SCHEMA.matches(signature)
    True

  <Arguments>
    key_dict:
      A dictionary containing the RSA keys and other identifying information.
      'rsakey_dict' has the form:
    
      {'keytype': 'rsa',
       'keyid': keyid,
       'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                  'private': '-----BEGIN RSA PRIVATE KEY----- ...'}}

      The public and private keys are in PEM format and stored as strings.

    data:
      Data object used by create_signature() to generate the signature.

  <Exceptions>
    TypeError, if a private key is not defined for 'rsakey_dict'.

    tuf.FormatError, if an incorrect format is found for the
    'rsakey_dict' object.

  <Side Effects>
    PyCrypto's 'Crypto.Signature.PKCS1_PSS' called to perform the actual
    signing.

  <Returns>
    A signature dictionary conformat to 'tuf.format.SIGNATURE_SCHEMA'.
  """

  # Does 'rsakey_dict' have the correct format?
  # This check will ensure 'rsakey_dict' has the appropriate number
  # of objects and object types, and that all dict keys are properly named.
  # Raise 'tuf.FormatError' if the check fails.
  tuf.formats.ANYKEY_SCHEMA.check_match(key_dict)
  
  # Raise 'tuf.Error' if 'tuf.conf.CRYPTO_LIBRARY' is not supported or could
  # not be imported.
  _check_crypto_libraries()

  # Signing the 'data' object requires a private key.
  # The 'PyCrypto-PKCS#1 PSS' (i.e., PyCrypto module) signing method is the
  # only method currently supported.
  signature = {}
  keytype = key_dict['keytype']
  public = key_dict['keyval']['public']
  private = key_dict['keyval']['private']
  keyid = key_dict['keyid']
  method = None
  sig = None
 
  if keytype == 'rsa':
    if _RSA_CRYPTO_LIBRARY == 'pycrypto':
      sig, method = tuf.pycrypto_keys.create_signature(private, data)
    else:
      message = 'Unsupported "tuf.conf.RSA_CRYPTO_LIBRARY": '+\
        repr(_RSA_CRYPTO_LIBRARY)+'.'
      raise tuf.Error(message)
  elif keytype == 'ed25519':
    public = binascii.unhexlify(public)
    private = binascii.unhexlify(private)
    if _ED25519_CRYPTO_LIBRARY == 'pynacl' and 'pynacl' in _available_crypto_libraries:
      sig, method = tuf.ed25519_keys.create_signature(public, private,
                                                      data, use_pynacl=True)
    else:
      sig, method = tuf.ed25519_keys.create_signature(public, private,
                                                      data, use_pynacl=False)
  else:
    raise TypeError('Invalid key type.')
    
  # Build the signature dictionary to be returned.
  # The hexadecimal representation of 'sig' is stored in the signature.
  signature['keyid'] = keyid
  signature['method'] = method
  signature['sig'] = binascii.hexlify(sig)

  return signature





def verify_signature(key_dict, signature, data):
  """
  <Purpose>
    Determine whether the private key belonging to 'rsakey_dict' produced
    'signature'.  verify_signature() will use the public key found in
    'rsakey_dict', the 'method' and 'sig' objects contained in 'signature',
    and 'data' to complete the verification.  Type-checking performed on both
    'rsakey_dict' and 'signature'.

    >>> ed25519_key = generate_ed25519_key()
    >>> data = 'The quick brown fox jumps over the lazy dog'
    >>> signature = create_signature(ed25519_key, data)
    >>> verify_signature(ed25519_key, signature, data)
    True
    >>> verify_signature(ed25519_key, signature, 'bad_data')
    False
    >>> rsa_key = generate_rsa_key()
    >>> signature = create_signature(rsa_key, data)
    >>> verify_signature(rsa_key, signature, data)
    True
    >>> verify_signature(rsa_key, signature, 'bad_data')
    False


  <Arguments>
    key_dict:
      A dictionary containing the RSA keys and other identifying information.
      'rsakey_dict' has the form:
     
      {'keytype': 'rsa',
       'keyid': keyid,
       'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                  'private': '-----BEGIN RSA PRIVATE KEY----- ...'}}

      The public and private keys are in PEM format and stored as strings.
      
    signature:
      The signature dictionary produced by tuf.rsa_key.create_signature().
      'signature' has the form:
      {'keyid': keyid, 'method': 'method', 'sig': sig}.  Conformant to
      'tuf.formats.SIGNATURE_SCHEMA'.
      
    data:
      Data object used by tuf.rsa_key.create_signature() to generate
      'signature'.  'data' is needed here to verify the signature.

  <Exceptions>
    tuf.UnknownMethodError.  Raised if the signing method used by
    'signature' is not one supported by tuf.rsa_key.create_signature().
    
    tuf.FormatError. Raised if either 'rsakey_dict'
    or 'signature' do not match their respective tuf.formats schema.
    'rsakey_dict' must conform to 'tuf.formats.RSAKEY_SCHEMA'.
    'signature' must conform to 'tuf.formats.SIGNATURE_SCHEMA'.

  <Side Effects>
    Crypto.Signature.PKCS1_PSS.verify() called to do the actual verification.

  <Returns>
    Boolean.  True if the signature is valid, False otherwise.
  """

  # Does 'rsakey_dict' have the correct format?
  # This check will ensure 'rsakey_dict' has the appropriate number
  # of objects and object types, and that all dict keys are properly named.
  # Raise 'tuf.FormatError' if the check fails.
  tuf.formats.ANYKEY_SCHEMA.check_match(key_dict)

  # Does 'signature' have the correct format?
  tuf.formats.SIGNATURE_SCHEMA.check_match(signature)
  
  # Using the public key belonging to 'rsakey_dict'
  # (i.e., rsakey_dict['keyval']['public']), verify whether 'signature'
  # was produced by rsakey_dict's corresponding private key
  # rsakey_dict['keyval']['private'].  Before returning the Boolean result,
  # ensure 'PyCrypto-PKCS#1 PSS' was used as the signing method.
  method = signature['method']
  sig = signature['sig']
  sig = binascii.unhexlify(sig)
  public = key_dict['keyval']['public']
  keytype = key_dict['keytype']
  valid_signature = False
  
  if keytype == 'rsa':
    if _RSA_CRYPTO_LIBRARY == 'pycrypto':
      valid_signature = tuf.pycrypto_keys.verify_signature(sig, method,
                                                           public, data) 
    else:
      message = 'Unsupported "tuf.conf.RSA_CRYPTO_LIBRARY": '+\
        repr(_RSA_CRYPTO_LIBRARY)+'.'
      raise tuf.Error(message) 
  elif keytype == 'ed25519':
    public = binascii.unhexlify(public)
    if _RSA_CRYPTO_LIBRARY == 'pynacl' and 'pynacl' in _available_crypto_libraries:
      valid_signature = tuf.ed25519_keys.verify_signature(public,
                                                          method, sig, data,
                                                          use_pynacl=True)
    else:
      valid_signature = tuf.ed25519_keys.verify_signature(public,
                                                          method, sig, data,
                                                          use_pynacl=False)
  else:
    raise TypeError('Unsupported key type.')

  return valid_signature 



if __name__ == '__main__':
  # The interactive sessions of the documentation strings can
  # be tested by running 'keys.py' as a standalone module.
  # python -B keys.py
  import doctest
  doctest.testmod()
