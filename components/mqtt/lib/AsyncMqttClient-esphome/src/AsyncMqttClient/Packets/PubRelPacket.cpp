#include "PubRelPacket.hpp"

using AsyncMqttClientInternals::PubRelPacket;

PubRelPacket::PubRelPacket(ParsingInformation* parsingInformation, OnPubRelInternalCallback callback)
: _parsingInformation(parsingInformation)
, _callback(callback)
, _bytePosition(0)
, _packetIdMsb(0)
, _packetId(0) {
}

PubRelPacket::~PubRelPacket() {
}

void PubRelPacket::parseVariableHeader(uint8_t* data, size_t len, size_t* currentBytePosition) {
  uint8_t currentByte = data[(*currentBytePosition)++];
  if (_bytePosition++ == 0) {
    _packetIdMsb = currentByte;
  } else {
    _packetId = currentByte | _packetIdMsb << 8;
    _parsingInformation->bufferState = BufferState::NONE;
    _callback(_packetId);
  }
}

void PubRelPacket::parsePayload(uint8_t* data, size_t len, size_t* currentBytePosition) {
  (void)data;
  (void)currentBytePosition;
}
