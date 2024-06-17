import Foundation

public class IndraEvent: Codable {
  var domain: String = ""
  var from_id: String = ""
  var uuid4: String = UUID().uuidString
  var parent_uuid4: String = ""
  var seq_no: Int = 0
  var to_scope: String = ""
  var time_jd_start: Double = Date().timeIntervalSince1970  // XXX Julian date! Wrong!
  var data_type: String = ""
  var data: String = ""
  var auth_hash: String = ""
  var time_jd_end: Double?

  init() {
    // No initialization logic required
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

  public static func timeToJulian(year: Int, month: Int, day: Int, hour: Int, minute: Int, second: Int, microsecond: Int) -> Double {
    // Convert (extended) Gregorian date to Julian date
      // Apple's uttlery ridiculous Swift type-checker fails on primary-school level math!
      let temp_0: Double = Double(367 * year) - Double(7 * (year + ((month + 9) / 12)))
      let temp_1: Double = temp_0 / 4.0 + Double(275 * month) / 9.0
      var jd: Double = Double(temp_1 + Double(day) + 1721013.5)
    jd += (Double(hour) + (Double(minute) / 60.0) + (Double(second) / 3600.0) + (Double(microsecond) / 3600000000.0))
    return jd
  }

  public static func julianToTime(jd: Double) -> (year: Int, month: Int, day: Int, hour: Int, minute: Int, second: Int, microsecond: Int) {
    // Convert Julian date to discrete time
    let jd = jd + 0.5
    let Z = Int(jd)
    let F: Double = jd - Double(Z)
    let A: Int
    if Z < 2299161 {
        A = Z
    } else {
        let alpha = Int((Double(Z) - 1867216.25) / 36524.25)
        A = Z + 1 + alpha - Int(Double(alpha) / 4)
    }
    let B = A + 1524
    let C = Int((Double(B) - 122.1) / 365.25)
    let D = Int(365.25 * Double(C))
    let E = Int((Double(B) - Double(D)) / 30.6001)
      let day: Double = Double(B) - Double(D) - Double(30.6001 * Double(E)) + F
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
    let microsecond = Int(1000000 * (Double(second) - Double(Int(second))))

    return (year, month, Int(day), hour, minute, second, microsecond)
  }

public static func timeToJulian(year: Int, month: Int, day: Int, hour: Int, minute: Int, second: Int, microsecond: Int) -> Double? {
    // Convert discrete time to Julian date, assume Julian calendar for time < 1582 otherwise Gregorian calendar
    if year == 0 {
        print("There is no year 0 in the Julian calendar! Use toTimeGregorian for continuous use of the extended Gregorian calendar.")
        return nil
    }
    
    // The new calendar was developed by Aloysius Lilius (about 1510 - 1576) and Christophorus Clavius (1537/38 - 1612).
    // It was established by a papal bull of Pope Gregory XIII that Thursday, October 4th, 1582, should be followed by Friday, October 15th, 1582.
    // This shifted the date of the vernal equinox to its proper date.
    // (https://www.ptb.de/cms/en/ptb/fachabteilungen/abt4/fb-44/ag-441/realisation-of-legal-time-in-germany/gregorian-calendar.html)
    if year == 1582 && month == 10 && day > 4 && day < 15 {
        print("The dates 5 - 14 Oct 1582 do not exist in the Gregorian calendar! Use toTimeGregorian for continuous use of the extended Gregorian calendar.")
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

}
