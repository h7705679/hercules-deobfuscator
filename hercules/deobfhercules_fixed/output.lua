-- Decompiled by deobfhercules (nested VM-in-BytecodeEncoder path)
-- Recovery method: BE-extract source → detect VM payload → decode VM bytecode → decompile
-- Outer BytecodeEncoder raw: 137268 bytes
-- Embedded VM-runtime source: 93765 bytes
-- Inner VM bytecode raw: 6902 bytes
-- VM top-level: 53 instructions, 22 constants, 5 sub-protos

-- Decompiled by deobfhercules (Hercules VM path, v2 decompiler)
-- Top-level: 53 instructions, 22 constants, 5 sub-protos
-- Raw bytecode: 6902 bytes
--
-- Recovered constants (strings and numbers found in the bytecode):
--   top-level (22 constants):
--     K0: "print"
--     K1: "math"
--     K2: "huge"
--     K3: "string"
--     K4: "char"
--     K5: "table"
--     K6: "concat"
--     K7: "insert"
--     K8: 107
--     K9: "k"
--     K10: 118
--     K11: "v"
--     K12: 104
--     K13: "h"
--     K14: 112
--     K15: "p"
--     K16: 94
--     K17: "n"
--     K18: 14
--     K19: 3
--     K20: 74
--     K21: 24
--     sub-proto depth 1 (2 constants):
--       K0: 118
--       K1: 21
--       sub-proto depth 2 (15 constants):
--         K0: 1
--         K1: "byte"
--         K2: 48
--         K3: 57
--         K4: 10
--         K5: 65
--         K6: 90
--         K7: 26
--         K8: 97
--         K9: 122
--         K10: "table"
--         K11: "insert"
--         K12: "string"
--         K13: "char"
--         K14: "concat"
--         sub-proto depth 3 (6 constants):
--           K0: 48
--           K1: 57
--           K2: 65
--           K3: 90
--           K4: 97
--           K5: 122



--     sub-proto depth 1 (15 constants):
--       K0: 1
--       K1: "byte"
--       K2: 48
--       K3: 57
--       K4: 10
--       K5: 65
--       K6: 90
--       K7: 26
--       K8: 97
--       K9: 122
--       K10: "table"
--       K11: "insert"
--       K12: "string"
--       K13: "char"
--       K14: "concat"
--       sub-proto depth 2 (6 constants):
--         K0: 48
--         K1: 57
--         K2: 65
--         K3: 90
--         K4: 97
--         K5: 122


--     sub-proto depth 1 (3 constants):
--       K0: "wait"
--       K1: "math"
--       K2: "huge"

--     sub-proto depth 1 (2 constants):
--       K0: 104
--       K1: 20
--       sub-proto depth 2 (15 constants):
--         K0: 1
--         K1: "byte"
--         K2: 48
--         K3: 57
--         K4: 10
--         K5: 65
--         K6: 90
--         K7: 26
--         K8: 97
--         K9: 122
--         K10: "table"
--         K11: "insert"
--         K12: "string"
--         K13: "char"
--         K14: "concat"
--         sub-proto depth 3 (6 constants):
--           K0: 48
--           K1: 57
--           K2: 65
--           K3: 90
--           K4: 97
--           K5: 122



--     sub-proto depth 1 (15 constants):
--       K0: 1
--       K1: "byte"
--       K2: 48
--       K3: 57
--       K4: 10
--       K5: 65
--       K6: 90
--       K7: 26
--       K8: 97
--       K9: 122
--       K10: "table"
--       K11: "insert"
--       K12: "string"
--       K13: "char"
--       K14: "concat"
--       sub-proto depth 2 (6 constants):
--         K0: 48
--         K1: 57
--         K2: 65
--         K3: 90
--         K4: 97
--         K5: 122



local v0 = math["huge"]
local v1 = string["char"]
local v2 = table["concat"]
local v3 = table["insert"]
local fn_main_P0 = function(...)
        local v0 = print
        -- proto 0 elided (antitamper/string-decoder)
        local v1 = @TABLE{107:"k",118:"v",104:"h",112:"p"}
        local v2 = 21
        print("a")
        return
end
fn_main_P0()
n = print
-- proto 1 elided (antitamper/string-decoder)
local v4 = "p"
local v5 = 14
print("b")
print = false
false = true
R7 = false
false = true
local fn_main_P2 = function(...)
        local v0 = math["huge"]
        wait(math["huge"])
        return
end
fn_main_P2()
local fn_main_P3 = function(...)
        local v0 = print
        -- proto 0 elided (antitamper/string-decoder)
        local v1 = @TABLE{107:"k",118:"v",104:"h",112:"p"}
        local v2 = 20
        print("n")
        return
end
fn_main_P3()
fn_main_P3 = print
-- proto 4 elided (antitamper/string-decoder)
R8 = "k"
R9 = 24
print("m")
return