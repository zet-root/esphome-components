#include "PingRespPacket.hpp"

using AsyncMqttClientInternals::PingRespPacket;

PingRespPacket::PingRespPacket(ParsingInformation* parsingInformation, OnPingRespInternalCallback callback)
: _parsingInformation(parsingInformation)
, _callback(callback) {
}

PingRespPacket::~PingRespPacket() {
}

void PingRespPacket::parseVariableHeader(uint8_t* data, size_t len, size_t* currentBytePosition) {
  (void)data;
  (void)currentBytePosition;
}

void PingRespPacket::parsePayload(uint8_t* data, size_t len, size_t* currentBytePosition) {
  (void)data;
  (void)currentBytePosition;
}
