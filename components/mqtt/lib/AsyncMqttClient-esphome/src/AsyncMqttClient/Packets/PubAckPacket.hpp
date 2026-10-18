#pragma once

#include "Arduino.h"
#include "Packet.hpp"
#include "../ParsingInformation.hpp"
#include "../Callbacks.hpp"

namespace AsyncMqttClientInternals {
class PubAckPacket : public Packet {
 public:
  explicit PubAckPacket(ParsingInformation* parsingInformation, OnPubAckInternalCallback callback);
  ~PubAckPacket();

  void parseVariableHeader(uint8_t* data, size_t len, size_t* currentBytePosition);
  void parsePayload(uint8_t* data, size_t len, size_t* currentBytePosition);

 private:
  ParsingInformation* _parsingInformation;
  OnPubAckInternalCallback _callback;

  uint8_t _bytePosition;
  uint8_t _packetIdMsb;
  uint16_t _packetId;
};
}  // namespace AsyncMqttClientInternals
