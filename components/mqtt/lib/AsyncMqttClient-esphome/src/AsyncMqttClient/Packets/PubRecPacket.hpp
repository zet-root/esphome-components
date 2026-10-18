#pragma once

#include "Arduino.h"
#include "Packet.hpp"
#include "../ParsingInformation.hpp"
#include "../Callbacks.hpp"

namespace AsyncMqttClientInternals {
class PubRecPacket : public Packet {
 public:
  explicit PubRecPacket(ParsingInformation* parsingInformation, OnPubRecInternalCallback callback);
  ~PubRecPacket();

  void parseVariableHeader(uint8_t* data, size_t len, size_t* currentBytePosition);
  void parsePayload(uint8_t* data, size_t len, size_t* currentBytePosition);

 private:
  ParsingInformation* _parsingInformation;
  OnPubRecInternalCallback _callback;

  uint8_t _bytePosition;
  uint8_t _packetIdMsb;
  uint16_t _packetId;
};
}  // namespace AsyncMqttClientInternals
