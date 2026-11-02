#pragma once
// Proposed TEMP revision only. Not enabled on the canonical 561-part board.
// Task-owned policy; the acquisition owner publishes complete immutable cohorts.
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>

namespace V4ThermalProposal {
constexpr uint64_t SETTLE_US=20000, MAX_AGE_US=500000, MAX_SPAN_US=2000;
constexpr uint8_t BANK=0, FIRST_SLOT=10, SETTLE_PER_READ_US=24;
enum class Fault : uint8_t { None, Configuration, Clock, Stale, Timing,
    Sequence, Adc, Reference, Short, Open, Range, Hot };
enum Slot : unsigned { Pack=0, Base=1, Midpoint=2, Excitation=3 };
struct Cohort {
    uint32_t sequence=0;
    std::array<int32_t,4> code{}; // Signed ADC values, widened before validation.
    std::array<uint64_t,4> stampUs{};
    bool ioGood=true;
};
struct Calibration { double midpointRatio=.5, packPullOhm=10000, basePullOhm=10000; };
struct Reading {
    Fault fault=Fault::None;
    double packC=std::numeric_limits<double>::quiet_NaN();
    double baseC=std::numeric_limits<double>::quiet_NaN();
};
struct TablePoint { double c, ohm; };
// Semitec 103AT-2 nominal table, identical to ../calculate.py.
constexpr std::array<TablePoint,19> TABLE{{
    {-50,329500},{-40,188500},{-30,111300},{-20,67770},{-10,42470},
    {0,27280},{10,17960},{20,12090},{25,10000},{30,8313},{40,5827},
    {50,4160},{60,3020},{70,2228},{80,1668},{85,1451},{90,1266},
    {100,973.1},{110,757.6}
}};
inline double temperature(double ohm) {
    if(!std::isfinite(ohm) || ohm>TABLE.front().ohm || ohm<TABLE.back().ohm)
        return std::numeric_limits<double>::quiet_NaN();
    for(unsigned i=0;i+1<TABLE.size();++i) {
        const auto a=TABLE[i], b=TABLE[i+1];
        if(ohm<=a.ohm && ohm>=b.ohm)
            return a.c+(b.c-a.c)*std::log(ohm/a.ohm)/std::log(b.ohm/a.ohm);
    }
    return std::numeric_limits<double>::quiet_NaN();
}
inline bool calibrationValid(const Calibration& c) {
    return std::isfinite(c.midpointRatio) && c.midpointRatio>=.48 && c.midpointRatio<=.52
        && std::isfinite(c.packPullOhm) && c.packPullOhm>=9900 && c.packPullOhm<=10100
        && std::isfinite(c.basePullOhm) && c.basePullOhm>=9900 && c.basePullOhm<=10100;
}
inline Reading decode(const Cohort& s,const Calibration& c={}) {
    Reading out;
    if(!calibrationValid(c)){out.fault=Fault::Configuration;return out;}
    if(!s.ioGood){out.fault=Fault::Adc;return out;}
    for(auto value:s.code)if(value<-32768 || value>32767){out.fault=Fault::Adc;return out;}
    const int32_t dm=s.code[Midpoint], span=s.code[Excitation]-dm;
    if(dm<-200 || dm>200 || span<12800 || span>14500){out.fault=Fault::Reference;return out;}
    double values[2]{};
    for(unsigned i=0;i<2;++i) {
        const double x=double(s.code[i]-dm)/span;
        const double q=c.midpointRatio+(1-c.midpointRatio)*x;
        if(q<.06){out.fault=Fault::Short;return out;}
        if(q>.94){out.fault=Fault::Open;return out;}
        const double pull=i==Pack?c.packPullOhm:c.basePullOhm;
        values[i]=temperature(pull*q/(1-q));
        if(!std::isfinite(values[i])){out.fault=Fault::Range;return out;}
    }
    out.packC=values[Pack];out.baseC=values[Base];return out;
}

struct Decision {
    bool captureAllowed=false, chargingDisabled=true, stopRequested=false;
    Fault fault=Fault::None;
};
// Single task owns this object. Caller must atomically publish stopRequested to
// every load owner. No reset method: a latched fault requires a fresh boot.
// The acquisition owner assigns sequence only after four real conversions. A
// replay with newly forged sequence/timestamps is not observable here. poll()
// needs a live task; independent watchdog/actuator supervision remains required.
class Gate {
    Calibration calibration_;
    uint64_t readyUs_, lastNow_, firstStamp_=0, lastStamp_=0;
    uint32_t sequence_=0;
    unsigned coolCount_=0, hotCount_=0;
    bool haveCohort_=false, running_=false;
    Fault fault_=Fault::None;
    Decision decision() const {
        const bool allowed=running_ && fault_==Fault::None;
        return {allowed,!allowed,fault_!=Fault::None,fault_};
    }
    Decision fail(Fault why){if(fault_==Fault::None)fault_=why;running_=false;return decision();}
public:
    // readyUs is the actual rail-ready timestamp, not the command-to-enable time.
    explicit Gate(uint64_t readyUs,const Calibration& c={}):calibration_(c),
        readyUs_(readyUs),lastNow_(readyUs) {
        if(!calibrationValid(c))fault_=Fault::Configuration;
    }
    Decision poll(uint64_t now) {
        if(fault_!=Fault::None)return decision();
        if(now<lastNow_)return fail(Fault::Clock);
        lastNow_=now;
        const uint64_t origin=haveCohort_?firstStamp_:readyUs_;
        if(now-origin>MAX_AGE_US)return fail(Fault::Stale);
        return decision();
    }
    Decision update(const Cohort& s,uint64_t now) {
        if(poll(now).stopRequested)return decision();
        const uint64_t first=s.stampUs.front(),last=s.stampUs.back();
        if(first<readyUs_ || first-readyUs_<SETTLE_US || last>now)
            return fail(Fault::Timing);
        for(unsigned i=1;i<4;++i)
            if(s.stampUs[i]<=s.stampUs[i-1])return fail(Fault::Timing);
        if(last-first>MAX_SPAN_US)return fail(Fault::Timing);
        if(now-first>MAX_AGE_US)return fail(Fault::Stale);
        if(haveCohort_ && (s.sequence!=uint32_t(sequence_+1) || first<=lastStamp_))
            return fail(Fault::Sequence);
        const auto value=decode(s,calibration_);
        if(value.fault!=Fault::None)return fail(value.fault);
        haveCohort_=true;firstStamp_=first;lastStamp_=last;sequence_=s.sequence;
        // Provisional indicated-temperature thresholds, not a wearability claim.
        const bool hot=value.packC>=45 || value.baseC>=36;
        hotCount_=hot?hotCount_+1:0;
        if(hotCount_>=2)return fail(Fault::Hot);
        if(!running_) {
            const bool cool=value.packC<=40 && value.baseC<=33;
            coolCount_=cool?coolCount_+1:0;
            if(coolCount_>=2)running_=true;
        }
        return decision();
    }
};
} // namespace V4ThermalProposal
