import Foundation

/// A class representing an Indra event.
public class IndraEvent: Codable {
  var domain: String = ""
  var from_id: String = ""
  var uuid4: String = UUID().uuidString
  var parent_uuid4: String = ""
  var seq_no: Int = 0
  var to_scope: String = ""
  var time_jd_start: Double = 0.0
  var data_type: String = ""
  var data: String = ""
  var auth_hash: String = ""
  var time_jd_end: Double?

  init() {
    // get current time (utc):
    let now = Date()
    time_jd_start = IndraEvent.dateToJulian(date: now)
  }

  public func to_json() -> String? {
    let encoder = JSONEncoder()
    encoder.outputFormatting = .prettyPrinted
    do {
      let jsonData = try encoder.encode(self)
      return String(data: jsonData, encoding: .utf8)
    } catch {
      print("Failed to convert IndraEvent to JSON: \(error)")
      return nil
    }
  }

  public static func from_json(json_str: String) -> IndraEvent? {
    let decoder = JSONDecoder()
    do {
      let jsonData = json_str.data(using: .utf8)!
      let indraEvent = try decoder.decode(IndraEvent.self, from: jsonData)
      return indraEvent
    } catch {
      print("Failed to convert JSON to IndraEvent: \(error)")
      return nil
    }
  }

  public static func mqcmp(pub: String, sub: String) -> Bool {
    let illegalChars = ["+", "#"]
    for c in illegalChars {
      if pub.contains(c) {
        print("Illegal char '\(c)' in pub in mqcmp!")
        return false
      }
    }

    var inds = 0
    var wcs = false

    for indp in pub.indices {
      if wcs {
        if pub[indp] == "/" {
          inds += 1
          wcs = false
        }
        continue
      }

      if inds >= sub.count {
        return false
      }

      if pub[indp] == sub[sub.index(sub.startIndex, offsetBy: inds)] {
        inds += 1
        continue
      }

      if sub[sub.index(sub.startIndex, offsetBy: inds)] == "#" {
        return true
      }

      if sub[sub.index(sub.startIndex, offsetBy: inds)] == "+" {
        wcs = true
        inds += 1
        continue
      }

      if pub[indp] != sub[sub.index(sub.startIndex, offsetBy: inds)] {
        // print("\(pub[indp...]) \(sub[sub.index(sub.startIndex, offsetBy: inds)...])")
        return false
      }
    }

    if sub[sub.index(sub.startIndex, offsetBy: inds)...].isEmpty {
      return true
    }

    if sub[sub.index(sub.startIndex, offsetBy: inds)...].count == 1 {
      if sub[sub.index(sub.startIndex, offsetBy: inds)] == "+"
        || sub[sub.index(sub.startIndex, offsetBy: inds)] == "#"
      {
        return true
      }
    }

    return false
  }

  public static func timeToJulianGreg(
    year: Int, month: Int, day: Int, hour: Int, minute: Int, second: Int, microsecond: Int
  ) -> Double {
    // Convert (extended) Gregorian date to Julian date
    // Apple's uttlery ridiculous Swift type-checker fails on primary-school level math!
    let temp_0: Double = Double(367 * year) - Double(7 * (year + ((month + 9) / 12)))
    let temp_1: Double = temp_0 / 4.0 + Double(275 * month) / 9.0
    var jd: Double = Double(temp_1 + Double(day) + 1721013.5)
    jd +=
      (Double(hour) + (Double(minute) / 60.0) + (Double(second) / 3600.0)
        + (Double(microsecond) / 3600000000.0))
    return jd
  }

  public static func julianToTime(jd: Double) -> (
    year: Int, month: Int, day: Int, hour: Int, minute: Int, second: Int, microsecond: Int
  ) {
    // Convert Julian date to discrete time
    let jd = jd + 0.5
    let Z = Int(jd)
    let F: Double = jd - Double(Z)
    let A: Int
    if Z < 2_299_161 {
      A = Z
    } else {
      let alpha = Int((Double(Z) - 1867216.25) / 36524.25)
      A = Z + 1 + alpha - Int(Double(alpha) / 4)
    }
    let B = A + 1524
    let C = Int((Double(B) - 122.1) / 365.25)
    let D = Int(365.25 * Double(C))
    let E = Int((Double(B) - Double(D)) / 30.6001)
    let day: Int = B - D - Int(30.6001 * Double(E)) + Int(F)
    let month: Int
    if E < 14 {
      month = E - 1
    } else {
      month = E - 13
    }
    let year: Int
    if month > 2 {
      year = C - 4716
    } else {
      year = C - 4715
    }
    let hour = Int(24 * (jd - Double(Int(jd))))
    let minute = Int(60 * (Double(hour) - Double(Int(hour))))
    let second = Int(60 * (Double(minute) - Double(Int(minute))))
    let microsecond = Int(1_000_000 * (Double(second) - Double(Int(second))))

    return (year, month, Int(day), hour, minute, second, microsecond)
  }

  public static func timeToJulian(
    year: Int, month: Int, day: Int, hour: Int, minute: Int, second: Int, microsecond: Int
  ) -> Double? {
    // Convert discrete time to Julian date, assume Julian calendar for time < 1582 otherwise Gregorian calendar
    if year == 0 {
      print(
        "There is no year 0 in the Julian calendar! Use toTimeGregorian for continuous use of the extended Gregorian calendar."
      )
      return nil
    }

    // The new calendar was developed by Aloysius Lilius (about 1510 - 1576) and Christophorus Clavius (1537/38 - 1612).
    // It was established by a papal bull of Pope Gregory XIII that Thursday, October 4th, 1582, should be followed by Friday, October 15th, 1582.
    // This shifted the date of the vernal equinox to its proper date.
    // (https://www.ptb.de/cms/en/ptb/fachabteilungen/abt4/fb-44/ag-441/realisation-of-legal-time-in-germany/gregorian-calendar.html)
    if year == 1582 && month == 10 && day > 4 && day < 15 {
      print(
        "The dates 5 - 14 Oct 1582 do not exist in the Gregorian calendar! Use toTimeGregorian for continuous use of the extended Gregorian calendar."
      )
      return nil
    }

    let jy: Int
    let jm: Int
    if month > 2 {
      jy = year
      jm = month + 1
    } else {
      jy = year - 1
      jm = month + 13
    }

    var intgr = floor(365.25 * Double(jy)) + floor(30.6001 * Double(jm)) + Double(day) + 1720995.0

    // check for switch to Gregorian calendar
    let gregcal = 15 + 31 * (10 + 12 * 1582)
    if Double(day) + 31 * (Double(month) + 12 * Double(year)) >= Double(gregcal) {
      let ja = floor(0.01 * Double(jy))
      intgr += 2 - ja + floor(0.25 * ja)
    }

    // correct for half-day offset
    var dayfrac = Double(hour) / 24.0 - 0.5
    if dayfrac < 0.0 {
      dayfrac += 1.0
      intgr -= 1
    }

    // now set the fraction of a day
    let frac = dayfrac + Double(minute + second) / 3600.0 / 24.0

    // round to nearest second (maybe not necessary?)
    let jd0 = (intgr + frac) * 100000.0
    var jd = floor(jd0)
    if jd0 - jd > 0.5 {
      jd += 1
    }
    jd /= 100000.0

    // add microsecond
    jd += Double(microsecond) / 86400000000.0

    return jd
  }

  public static func julianToISO(jd: Double) -> String {
    let (year, month, day, hour, minute, second, microsecond) = julianToTime(jd: jd)
    return String(
      format: "%d-%02d-%02dT%02d:%02d:%02d.%06dZ", year, month, day, hour, minute, second,
      microsecond)
  }

  public static func ISOToJulian(iso: String) -> Double? {
    // Convert extended ISO 8601 string to Julian date
    // Year may be negative and longer or shorter than 4 digits. Only UTC time is supported.
    var parts = iso.split(separator: "T")
    if parts.count != 2 {
      print("Invalid ISO 8601 string: \(iso)")
      return nil
    }
    let date = String(parts[0])
    let time = String(parts[1])
    if date.starts(with: "-") {
      parts = date.dropFirst().split(separator: "-")
      parts[0] = "-" + parts[0]
    } else {
      parts = date.split(separator: "-")
    }
    let year = Int(parts[0])!
    let month = Int(parts[1])!
    let day = Int(parts[2])!
    parts = time.split(separator: ":")
    let hour = Int(parts[0])!
    let minute = Int(parts[1])!
    parts = parts[2].split(separator: ".")
    let second = Int(parts[0])!
    let microsecond = Int(parts[1].dropLast())!
    return timeToJulian(
      year: year, month: month, day: day, hour: hour, minute: minute, second: second,
      microsecond: microsecond)
  }

  public static func dateToJulian(date: Date) -> Double {
    // UTC!
    let calendar = Calendar.current
    //convert to UTC
    let date = date.addingTimeInterval(TimeInterval(NSTimeZone.local.secondsFromGMT()))

    let year = calendar.component(.year, from: date)
    let month = calendar.component(.month, from: date)
    let day = calendar.component(.day, from: date)
    let hour = calendar.component(.hour, from: date)
    let minute = calendar.component(.minute, from: date)
    let second = calendar.component(.second, from: date)
    let microsecond = calendar.component(.nanosecond, from: date) / 1000
    let jd = timeToJulian(
      year: year, month: month, day: day, hour: hour, minute: minute, second: second,
      microsecond: microsecond)!
    return jd
  }

  public static func julianToDate(jd: Double) -> Date {
    let (year, month, day, hour, minute, second, microsecond) = julianToTime(jd: jd)
    var components = DateComponents()
    components.year = year
    components.month = month
    components.day = day
    components.hour = hour
    components.minute = minute
    components.second = second
    components.nanosecond = microsecond * 1000
    components.timeZone = TimeZone(abbreviation: "UTC")
    let calendar = Calendar.current
    return calendar.date(from: components)!
  }

  public static func julianToStringTime(jd: Double) -> String {
    // Convert Julian date to string time
    // this uses datetime for 1 AD and later,
    // and BC dates between 1 AD and 13000 BP and BP or kya BP dates for older
    if jd < 1_721_423.5 {  // 1 AD
      // > 13000 BP? Use BC, else use BP, and if < 100000 BP use kya BP
      if jd > 1_721_423.5 - 13_000 * 365.25 {
        // BC
        // var (year, month, day, hour, minute, second, microsecond) = julianToTime(jd: jd)
        var (year, _, _, _, _, _, _) = julianToTime(jd: jd)
        // bc = int((1721423.5 - jd) / 365.25) + 1
        year = 1 - year
        return "\(year) BC"
      } else if jd > 1_721_423.5 - 100_000 * 365.25 {
        // BP
        let bp = Int((1_721_423.5 - jd) / 365.25)
        return "\(bp) BP"
      } else {
        // kya BP
        let kya = Int((1_721_423.5 - jd) / (1000 * 365.25))
        return "\(kya) kya BP"
      }
    } else {
      // AD
      // dt = IndraTime.julian_to_datetime(jd)
      // let (year, month, day, hour, minute, second, microsecond) = julianToTime(jd: jd)
      let (year, month, day, _, _, _, _) = julianToTime(jd: jd)
      if month == 1 && day == 1 && year < 1900 {
        return String(year)
      } else if day == 1 && year < 1900 {
        return "\(year)-\(month)"
      } else {
        return "\(year)-\(month)-\(day)"
      }
    }
  }

}
