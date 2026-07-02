-- Decompiled by deobfhercules (nested VM-in-BytecodeEncoder path)
-- Recovery method: BE-extract source → detect VM payload → decode VM bytecode → decompile
-- Outer BytecodeEncoder raw: 56474 bytes
-- Embedded VM-runtime source: 34251 bytes
-- Inner VM bytecode raw: 1858 bytes
-- VM top-level: 16 instructions, 9 constants, 1 sub-protos

-- Decompiled by deobfhercules (Hercules VM path, v2 decompiler)
-- Top-level: 16 instructions, 9 constants, 1 sub-protos
-- Raw bytecode: 1858 bytes
--
-- Recovered constants (strings and numbers found in the bytecode):
--   top-level (9 constants):
--     K0: "print"
--     K1: "string"
--     K2: "char"
--     K3: "table"
--     K4: "concat"
--     K5: "insert"
--     K6: 70
--     K7: "F"
--     K8: 60
--     sub-proto depth 1 (2 constants):
--       K0: 70
--       K1: 13
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




local v0 = string["char"]
local v1 = table["concat"]
local v2 = table["insert"]
local fn_main_P0 = function(...)
        local v0 = print
        -- proto 0 elided (antitamper/string-decoder)
        local v1 = @TABLE{70:"F"}
        local v2 = 13
        print("S")
        return
end
fn_main_P0()
return