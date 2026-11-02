#include "thermal.hpp"
#include <cassert>
#include <climits>
#include <iostream>
#include <random>
using namespace V4ThermalProposal;
static unsigned checks=0;
static void check(bool condition){++checks;assert(condition);}
static Cohort sample(uint32_t seq=0,uint64_t start=25000,double packR=10000,double baseR=10000) {
    Cohort c;c.sequence=seq;
    for(unsigned i=0;i<4;++i)c.stampUs[i]=start+i*250;
    c.code[Midpoint]=0;c.code[Excitation]=13653;
    c.code[Pack]=int32_t(std::lround((2*packR/(10000+packR)-1)*13653));
    c.code[Base]=int32_t(std::lround((2*baseR/(10000+baseR)-1)*13653));
    return c;
}
static void fault(const Decision& d,Fault expected) {
    check(d.fault==expected);check(d.stopRequested);
    check(!d.captureAllowed);check(d.chargingDisabled);
}
int main() {
    for(auto row:TABLE)check(std::abs(temperature(row.ohm)-row.c)<1e-10);
    check(std::abs(temperature(std::sqrt(8313*5827))-35)<1e-10);
    check(std::isnan(temperature(0)));check(std::isnan(temperature(INFINITY)));
    check(std::isnan(temperature(NAN)));check(std::isnan(temperature(330000)));
    auto c=sample();auto r=decode(c);check(r.fault==Fault::None);
    check(r.packC==25 && r.baseC==25);
    r=decode(sample(0,25000,5827,4160));
    check(std::abs(r.packC-40)<.005 && std::abs(r.baseC-50)<.005);
    for(auto row:TABLE) {
        r=decode(sample(0,25000,row.ohm,row.ohm));
        if(row.c>=-30 && row.c<=100) {
            check(r.fault==Fault::None);check(std::abs(r.packC-row.c)<.02);
        } else check(r.fault!=Fault::None);
    }
    for(unsigned slot=0;slot<4;++slot)for(int32_t bad:{INT32_MIN,-32769,32768,INT32_MAX}){
        c=sample();c.code[slot]=bad;check(decode(c).fault==Fault::Adc);
    }
    c=sample();c.ioGood=false;check(decode(c).fault==Fault::Adc);
    for(int32_t midpoint:{-201,201}){c=sample();c.code[Midpoint]=midpoint;check(decode(c).fault==Fault::Reference);}
    for(int32_t span:{-32768,0,12799,14501}){c=sample();c.code[Excitation]=span;check(decode(c).fault==Fault::Reference);}
    for(int32_t span:{12800,14500}){c=sample();c.code[Excitation]=span;check(decode(c).fault==Fault::None);}
    for(unsigned slot=0;slot<2;++slot){
        c=sample();c.code[slot]=13653;check(decode(c).fault==Fault::Open);
        c.code[slot]=-13653;check(decode(c).fault==Fault::Short);
    }
    for(double invalid:{double(NAN),double(INFINITY),double(-INFINITY),0.,1.}){
        Calibration cal;cal.midpointRatio=invalid;check(decode(sample(),cal).fault==Fault::Configuration);
        Gate g(0,cal);fault(g.poll(0),Fault::Configuration);
    }
    for(double invalid:{double(NAN),double(INFINITY),0.,9899.,10101.}){
        Calibration cal;cal.packPullOhm=invalid;check(decode(sample(),cal).fault==Fault::Configuration);
        cal={};cal.basePullOhm=invalid;check(decode(sample(),cal).fault==Fault::Configuration);
    }
    // Independent affine-path check with a measured midpoint ratio.
    Calibration measured;measured.midpointRatio=.49;
    c=sample();c.code[Midpoint]=100;c.code[Excitation]=14000;
    c.code[Pack]=c.code[Base]=int32_t(std::lround(100+(.5-.49)/.51*13900));
    check(std::abs(decode(c,measured).packC-25)<.01);
    {
        Gate g(0);auto d=g.poll(0);check(!d.captureAllowed && d.chargingDisabled && !d.stopRequested);
        d=g.update(sample(),25750);check(!d.captureAllowed && !d.stopRequested);
        d=g.update(sample(1,125000),125750);check(d.captureAllowed && !d.chargingDisabled && !d.stopRequested);
        fault(g.poll(625001),Fault::Stale);
        fault(g.update(sample(2,700000),700750),Fault::Stale);
    }
    {Gate g(0);check(!g.poll(500000).stopRequested);fault(g.poll(500001),Fault::Stale);}
    {Gate g(1000);fault(g.poll(999),Fault::Clock);}
    {Gate g(0);g.poll(1000);fault(g.poll(999),Fault::Clock);}
    for(unsigned kind=0;kind<5;++kind){
        Gate g(0);c=sample();
        if(kind==0)c.stampUs[0]=19999;
        if(kind==1)c.stampUs[1]=c.stampUs[0];
        if(kind==2)c.stampUs[2]=c.stampUs[1]-1;
        if(kind==3)c.stampUs[3]=c.stampUs[0]+2001;
        fault(g.update(c,kind==4?25000:30000),Fault::Timing);
    }
    {Gate g(0);fault(g.update(sample(),525001),Fault::Stale);}
    for(unsigned kind=0;kind<4;++kind){
        Gate g(0);g.update(sample(10),25750);c=sample(11,125000);
        if(kind==0)c.sequence=10;
        if(kind==1)c.sequence=9;
        if(kind==2)c.sequence=12;
        if(kind==3)c=sample(11,25750);
        fault(g.update(c,125750),Fault::Sequence);
    }
    {Gate g(0);g.update(sample(UINT32_MAX),25750);check(g.update(sample(0,125000),125750).captureAllowed);}
    for(unsigned kind=0;kind<3;++kind){
        Gate g(0);g.update(sample(),25750);g.update(sample(1,125000),125750);
        c=sample(2,225000,kind==0?10000:4160,kind==1?10000:5827);
        check(g.update(c,225750).captureAllowed);
        c.sequence=3;for(auto& t:c.stampUs)t+=100000;
        fault(g.update(c,325750),Fault::Hot);
        fault(g.update(sample(4,425000),425750),Fault::Hot);
        fault(g.update(sample(5,525000),525750),Fault::Hot);
        Gate reboot(600000);
        check(!reboot.update(sample(0,625000,4160,5827),625750).captureAllowed);
        check(!reboot.update(sample(1,725000),725750).captureAllowed);
        check(reboot.update(sample(2,825000),825750).captureAllowed);
    }
    {
        Gate g(0);g.update(sample(),25750);
        check(g.update(sample(1,125000),125750).captureAllowed);
        check(g.update(sample(2,225000,4160),225750).captureAllowed);
        check(g.update(sample(3,325000),325750).captureAllowed);
        check(g.update(sample(4,425000,4160),425750).captureAllowed);
        c=sample(5,525000);c.ioGood=false;fault(g.update(c,525750),Fault::Adc);
    }
    {
        Gate g(0);
        check(!g.update(sample(0,25000,10000,8313),25750).captureAllowed);
        check(!g.update(sample(1,125000,10000,std::sqrt(8313*5827)),125750).captureAllowed);
        check(!g.update(sample(2,225000),225750).captureAllowed);
        check(g.update(sample(3,325000),325750).captureAllowed);
    }
    {
        const uint64_t ready=UINT64_MAX-1000000;
        Gate g(ready);check(!g.update(sample(0,ready+25000),ready+25750).stopRequested);
        check(g.update(sample(1,ready+125000),ready+125750).captureAllowed);
    }
    const auto deterministic=checks;
    std::mt19937 rng(0x54454d50);
    for(unsigned i=0;i<100000;++i){
        c=sample();for(auto& value:c.code)value=int32_t(rng()%100001)-50000;
        r=decode(c);
        if(r.fault==Fault::None){check(std::isfinite(r.packC)&&std::isfinite(r.baseC));check(r.packC>=-50&&r.packC<=110&&r.baseC>=-50&&r.baseC<=110);}
        else check(std::isnan(r.packC)&&std::isnan(r.baseC));
    }
    std::cout<<"{\"checks\":"<<checks<<",\"deterministic_assertions\":"<<deterministic<<",\"random_adc_vectors\":100000,\"passed\":true}\n";
}
