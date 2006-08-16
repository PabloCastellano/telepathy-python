# telepathy-python - Base classes defining the interfaces of the Telepathy framework
#
# Copyright (C) 2005 Collabora Limited
# Copyright (C) 2005 Nokia Corporation
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import dbus.service

from telepathy import *

class ChannelInterfaceIceSignalling(dbus.service.Interface):
    """
    """
    def __init__(self):
        self._interfaces.add(CHANNEL_INTERFACE_ICE_SIGNALLING)

    @dbus.service.signal(CHANNEL_INTERFACE_ICE_SIGNALLING, signature='os')
    def NewIceSessionHandler(self, session_handler, type):
        """
        Signal that a session handler object has been created. The client
        should create a session object and create streams for the streams
        within.

        Parameters:
        session_handler - object path of the new IceSessionHandler object
        type - string indicating type of session, eg "rtp"
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_ICE_SIGNALLING,
                         in_signature='', out_signature='a(os)')
    def GetSessionHandlers(self):
        """
        Returns all currently active session handlers on this channel
        as a list of (session_handler_path, type).
        """
        pass


class IceSessionHandler(dbus.service.Object):
    """
    An ICE session handler is an object that handles a number of synchronised
    media streams.
    """
    def __init__(self, bus_name, object_path):
        dbus.service.Object.__init__(self, bus_name, object_path)

    @dbus.service.method(ICE_SESSION_HANDLER, in_signature='',
                                              out_signature='')
    def Ready(self):
        """
        Inform the connection manager that a client is ready to handle
        this SessionHandler.
        """
        pass

    @dbus.service.method(ICE_SESSION_HANDLER, in_signature='us',
                                              out_signature='')
    def Error(self, errno, message):
        """
        Inform the connection manager that an error occured in this session.
        """
        pass

    @dbus.service.signal(ICE_SESSION_HANDLER, signature='ouuu')
    def NewIceStreamHandler(self, stream_handler, id, media_type, direction):
        """
        Emitted when a new ICE stream handler has been created for this
        session.

        Parameters:
        stream_handler - an object path to a new MediaStreamHandler
        id - the unique ID of the new stream
        media_type - enum for type of media that this stream should handle
          MEDIA_STREAM_TYPE_AUDIO = 0
          MEDIA_STREAM_TYPE_VIDEO = 1
        direction - enum for direction of this stream
          MEDIA_STREAM_DIRECTION_NONE = 0
          MEDIA_STREAM_DIRECTION_SEND = 1
          MEDIA_STREAM_DIRECTION_RECEIVE = 2
          MEDIA_STREAM_DIRECTION_BIDIRECTIONAL = 3
        """
        pass

class IceStreamHandler(dbus.service.Object):
    """
    Handles signalling the information pertaining to a specific ICE stream.
    A client should provide information to this handler as and when it is
    available.
    """
    def __init__(self, bus_name, object_path):
        dbus.service.Object.__init__(self, bus_name, object_path)

    @dbus.service.method(ICE_STREAM_HANDLER, in_signature='a(usuuua{ss})', 
                                             out_signature='')
    def Ready(self, codecs):
        """
        Inform the connection manager that a client is ready to handle
        this StreamHandler. Also provide it with info about all supported
        codecs.

        Parameters:
        codecs - as for SupportedCodecs
        """
        pass

    @dbus.service.method(ICE_STREAM_HANDLER, in_signature='us',
                                             out_signature='')
    def Error(self, errno, message):
        """
        Inform the connection manager that an error occured in this stream.

        Parameters:
        errno - id of error, one of the following:
          MEDIA_STREAM_ERROR_UNKNOWN = 0
          MEDIA_STREAM_ERROR_EOS = 1
        message - string describing the error
        """
        pass

    @dbus.service.method(ICE_STREAM_HANDLER, in_signature='sa(usuussduss)',
                                             out_signature='')
    def NewNativeCandidate(self, candidate_id, transports):
        """
        Inform this MediaStreamHandler that a new native transport candidate
        has been ascertained.

        Parameters:
        candidate_id - string identifier for this candidate
        transports - array of transports for this candidate with fields:
          component number
          ip (as a string)
          port
          enum for base network protocol
            MEDIA_STREAM_BASE_PROTO_UDP = 0
            MEDIA_STREAM_BASE_PROTO_TCP = 1
          string specifying proto subtype (e.g RTP)
          string specifying proto profile (e.g AVP)
          our preference value of this transport (double in range 0-1
          inclusive)
            1 signals most preferred transport
          transport type, one of the following:
            MEDIA_STREAM_TRANSPORT_TYPE_LOCAL = 0
              a local address
            MEDIA_STREAM_TRANSPORT_TYPE_DERIVED = 1
              an external address derived by a method such as STUN
            MEDIA_STREAM_TRANSPORT_TYPE_RELAY = 2
              an external stream relay
          username - string to specify a username if authentication
                     is required
          password - string to specify a password if authentication
                     is required
        """
        pass

    @dbus.service.method(ICE_STREAM_HANDLER, in_signature='',
                                             out_signature='')
    def NativeCandidatesPrepared(self):
        """
        Informs the connection manager that all possible native candisates
        have been discovered for the moment.
        """
        pass

    @dbus.service.method(ICE_STREAM_HANDLER, in_signature='ss',
                                             out_signature='')
    def NewActiveCandidatePair(self, native_candidate_id, remote_candidate_id):
        """
        Informs the connection manager that a valid candidate pair
        has been discovered and streaming is in progress.
        """
        pass

    @dbus.service.signal(ICE_STREAM_HANDLER, signature='ss')
    def SetActiveCandidatePair(self, native_candidate_id, remote_candidate_id):
        """
        Emitted by the connection manager to inform the client that a
        valid candidate pair has been discovered by the remote end
        and streaming is in progress.
        """
        pass

    @dbus.service.signal(ICE_STREAM_HANDLER, signature='a(sa(usuussduss))')
    def SetRemoteCandidateList(self, remote_candidates):
        """
        Signal emitted when the connection manager wishes to inform the
        client of all the available remote candidates at once.

        Parameters:
        remote_candidates - a list of candidate id and a list of transports
        as defined in NewNativeCandidate
        """
        pass

    @dbus.service.signal(ICE_STREAM_HANDLER, signature='sa(usuussduss)')
    def AddRemoteCandidate(self, candidate_id, transports):
        """
        Signal emitted when the connection manager wishes to inform the
        client of a new remote candidate.

        Parameters:
        candidate_id - string identifier for this candidate
        transports - array of transports for this candidate with fields,
                     as defined in NewNativeCandidate
        """
        pass

    @dbus.service.signal(ICE_STREAM_HANDLER, signature='s')
    def RemoveRemoteCandidate(self, candidate_id):
        """
        Signal emitted when the connection manager wishes to inform the
        client that the remote end has removed a previously usable
        candidate.

        Parameters:
        candidate_id - string identifier for remote candidate to drop
        """
        pass

    @dbus.service.method(ICE_STREAM_HANDLER, in_signature='u',
                                             out_signature='')
    def CodecChoice(self, codec_id):
        """
        Inform the connection manager of the current codec choice.
        """
        pass

    @dbus.service.method(ICE_STREAM_HANDLER, in_signature='u',
                                             out_signature='')
    def StreamState(self, state):
        """
        Informs the connection manager of the stream's current state, as
        as specified in Channel.Type.StreamedMedia::ListStreams.
        """
        pass

    @dbus.service.method(ICE_STREAM_HANDLER, in_signature='a(usuuua{ss})',
                                             out_signature='')
    def SupportedCodecs(self, codecs):
        """
        Inform the connection manager of the supported codecs for this session.
        This is called after the connection manager has emitted SetRemoteCodecs
        to notify what codecs are supported by the peer, and will thus be an
        intersection of all locally supported codecs (passed to Ready)
        and those supported by the peer.

        Parameters:
        codecs - list of codec info structures containing
            id of codec
            codec name
            media type
            clock rate of codec
            number of supported channels
            string key-value pairs for supported optional parameters
        """
        pass

    @dbus.service.signal(ICE_STREAM_HANDLER, signature='a(usuuua{ss})')
    def SetRemoteCodecs(self, codecs):
        """
        Signal emitted when the connectoin manager wishes to inform the
        client of the codecs supported by the remote end.

        Parameters:
        codecs - as for SupportedCodecs
        """
        pass

    @dbus.service.signal(ICE_STREAM_HANDLER, signature='b')
    def SetStreamPlaying(self, playing):
        """
        Signal emitted when the connection manager wishes to set the
        stream playing or stopped.
        """
        pass

