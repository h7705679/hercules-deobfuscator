-- Decompiled by deobfhercules (nested VM-in-BytecodeEncoder path)
-- Recovery method: BE-extract source → detect VM payload → decode VM bytecode → decompile
-- Outer BytecodeEncoder raw: 65631 bytes
-- Embedded VM-runtime source: 41007 bytes
-- Inner VM bytecode raw: 2403 bytes
-- VM top-level: 19 instructions, 6 constants, 4 sub-protos

-- Decompiled by deobfhercules (Hercules VM path, v2 decompiler)
-- Top-level: 19 instructions, 6 constants, 4 sub-protos
-- Raw bytecode: 2403 bytes
--
-- Recovered constants (strings and numbers found in the bytecode):
--   top-level (6 constants):
--     K0: "print"
--     K1: "string"
--     K2: "char"
--     K3: "table"
--     K4: "concat"
--     K5: "insert"
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


--     sub-proto depth 1 (2 constants):
--       K0: 2
--       K1: 3

--     sub-proto depth 1 (2 constants):
--       K0: 4
--       K1: 5

--     sub-proto depth 1 (3 constants):
--       K0: 10
--       K1: 2
--       K2: 3


local v0 = string["char"]
local v1 = table["concat"]
local v2 = table["insert"]
-- proto 0 elided (antitamper/string-decoder)
local fn_main_P1 = function(...)
        local v0 = print
        local fn_main_P1_P0 = function(...)
                    local v0 = (a1 + a2)
                    return (a1 + a2)
        end
        local v1 = 2
        local v2 = 3
        print(fn_main_P1_P0(2, 3))
        return
end
fn_main_P1()
local fn_main_P2 = function(...)
        local v0 = print
        local fn_main_P2_P0 = function(...)
                    local v0 = (a1 * a2)
                    return (a1 * a2)
        end
        local v1 = 4
        local v2 = 5
        print(fn_main_P2_P0(4, 5))
        return
end
fn_main_P2()
local fn_main_P3 = function(...)
        local v0 = print
        local fn_main_P3_P0 = function(...)
                    local v0 = (a1 + a2)
                    return (a1 + a2)
        end
        local v1 = 10
        local fn_main_P3_P1 = function(...)
                    local v0 = (a1 * a2)
                    return (a1 * a2)
        end
        local v2 = 2
        local v3 = 3
        print(fn_main_P3_P0(10, fn_main_P3_P1(2, 3)))
        return
end
fn_main_P3()
return