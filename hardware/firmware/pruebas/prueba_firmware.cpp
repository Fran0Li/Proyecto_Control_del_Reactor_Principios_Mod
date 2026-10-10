// Pruebas del firmware en la PC, sin Arduino: simula millis(), los pines y el Serial.
// Compilar y correr desde hardware/firmware/pruebas:
//   g++ -std=c++17 -Wall prueba_firmware.cpp -o prueba && ./prueba                    (5 botones)
//   g++ -std=c++17 -Wall -DUSAR_JOYSTICK=1 prueba_firmware.cpp -o prueba && ./prueba   (joystick)
#include "Arduino.h"
unsigned long t_ms=0; int analogico[20]; int digital[20]; SerialMock Serial;
#include "../control_reactor/control_reactor.ino"
#include <cassert>
#include <iostream>
void correr(unsigned long ms){ for(unsigned long i=0;i<ms;i++){ loop(); t_ms++; } }
std::vector<std::string> nuevas(size_t &desde){ std::vector<std::string> v(Serial.lineas.begin()+desde, Serial.lineas.end()); desde=Serial.lineas.size(); std::vector<std::string> sin_hb; for(auto&l:v) if(l!="HB") sin_hb.push_back(l); return sin_hb;}
void ver(const char*paso, std::vector<std::string> v, std::vector<std::string> esperado){
  std::cout<<paso<<": "; for(auto&l:v) std::cout<<"["<<l<<"] "; std::cout<<"\n";
  if(v!=esperado){ std::cout<<"  FALLA, esperado: "; for(auto&l:esperado) std::cout<<"["<<l<<"] "; std::cout<<"\n"; std::exit(1);} }
int main(){
  for(int i=0;i<20;i++){digital[i]=HIGH; analogico[i]=512;}
  size_t k=0; setup(); ver("arranque", nuevas(k), {"HELLO CR-PAD-01 1.0"});
  correr(2500); int hb=0; for(auto&l:Serial.lineas) if(l=="HB") hb++; std::cout<<"latidos en 2.5 s: "<<hb<<"\n"; assert(hb==2); nuevas(k);
#if USAR_JOYSTICK
  analogico[A0]=1023; correr(50); ver("palanca a la derecha", nuevas(k), {"BTN RIGHT PRESS"});
  analogico[A0]=512+250; correr(50); ver("vuelve a 250 (zona de histéresis)", nuevas(k), {});
  analogico[A0]=512; correr(50); ver("al centro", nuevas(k), {"BTN RIGHT RELEASE"});
  analogico[A1]=0; analogico[A0]=0; correr(50); ver("diagonal arriba-izquierda", nuevas(k), {"BTN UP PRESS","BTN LEFT PRESS"});
  analogico[A1]=512; analogico[A0]=512; correr(50); ver("suelta", nuevas(k), {"BTN UP RELEASE","BTN LEFT RELEASE"});
  // rebote: el botón de acción parpadea 5 ms y se estabiliza
  digital[6]=LOW; correr(5); digital[6]=HIGH; correr(5); digital[6]=LOW; correr(50); ver("acción con rebote", nuevas(k), {"BTN ACTION PRESS"});
  digital[6]=HIGH; correr(50); ver("suelta acción", nuevas(k), {"BTN ACTION RELEASE"});
  digital[7]=LOW; correr(50); digital[7]=HIGH; correr(50); ver("clic del joystick", nuevas(k), {"BTN ACTION PRESS","BTN ACTION RELEASE"});
  analogico[A0]=512+320; correr(3); analogico[A0]=512; correr(50); ver("toque de 3 ms (ruido) no cuenta", nuevas(k), {});
#else
  const char* n[5]={"UP","DOWN","LEFT","RIGHT","ACTION"};
  for(int i=0;i<5;i++){ digital[2+i]=LOW; correr(30); digital[2+i]=HIGH; correr(30);
    std::string a=std::string("BTN ")+n[i]+" PRESS", b=std::string("BTN ")+n[i]+" RELEASE"; ver(n[i], nuevas(k), {a,b}); }
  digital[2]=LOW; correr(5); digital[2]=HIGH; correr(5); digital[2]=LOW; correr(50); ver("arriba con rebote", nuevas(k), {"BTN UP PRESS"});
#endif
  std::cout<<"OK\n"; }
