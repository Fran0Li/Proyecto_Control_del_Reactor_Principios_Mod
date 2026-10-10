// Reemplazo mínimo de Arduino.h para compilar el firmware en la PC (solo para pruebas).
#pragma once
#include <string>
#include <vector>
#include <cstdio>
#define A0 14
#define A1 15
#define INPUT_PULLUP 2
#define OUTPUT 1
#define HIGH 1
#define LOW 0
extern unsigned long t_ms; extern int analogico[20]; extern int digital[20];
inline unsigned long millis(){return t_ms;}
inline int analogRead(int p){return analogico[p];}
inline int digitalRead(int p){return digital[p];}
inline void pinMode(int,int){}
inline void digitalWrite(int,int){}
struct SerialMock { std::string buf; std::vector<std::string> lineas;
  void begin(long){} void print(const char*s){buf+=s;} void println(const char*s){buf+=s; lineas.push_back(buf); buf.clear();} };
extern SerialMock Serial;
