import Foundation

class IndraEvent: Codable {
    var domain: String = ""
    var from_id: String = ""
    var uuid4: String = UUID().uuidString
    var to_scope: String = ""
    var time_jd_start: Double = Date().timeIntervalSince1970
    var data_type: String = ""
    var data: String = ""
    var auth_hash: String = ""
    var time_jd_end: Double?
    
    init() {
        // No initialization logic required
    }
    
    func to_json() -> String? {
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
    
    static func from_json(json_str: String) -> IndraEvent? {
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
    
    static func mqcmp(pub: String, sub: String) -> Bool {
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
            if sub[sub.index(sub.startIndex, offsetBy: inds)] == "+" || sub[sub.index(sub.startIndex, offsetBy: inds)] == "#" {
                return true
            }
        }
        
        return false
    }
}
