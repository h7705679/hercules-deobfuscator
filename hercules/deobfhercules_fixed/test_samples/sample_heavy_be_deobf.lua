-- Decompiled by deobfhercules (Lua 5.4 BytecodeEncoder path)
-- Recovery method: extracted embedded source from Proto.source
-- Embedded source: 25285 bytes
-- Bytecode chunk: 4 instructions, 0 constants, 1 sub-protos
-- Raw bytecode: 47997 bytes

(function (...)
    if true then
        local _ = 82
    end
    if true then
        local _ = 97
    end
    local haowax = 16;
    local function gvldmg(bllsro)
        local _ = 64
    end
    if false then
        local _ = 95
    end
    if true then
        local _ = 56
    end
    if true then
        local _ = 5
    end
    local rwmxzf = 64;
    local function qrefct(qwgcyq)
        local _ = 38
    end
    local function gngewt(vrtfpn)
        local _ = 6
    end
    local function pxymgb(pdmkmd)
        local _ = 81
    end
    local function ndqxft(cxkvst)
        local _ = 93
    end
    local function kgwiwb(dugull)
        local _ = 37
    end
    while false do
        local _ = 8 break
    end
    local thing = 226;
    local thing2 = 226;
    local counter = 0;
    while thing == thing2 and counter < 1 do
        thing = thing + 1;
        counter = counter + 1;
        if thing == thing2 then
            local tbl = {1, 2, 3};
            table.sort(tbl, function (a, b)
                return a > b
            end);
            else do
                do
                    local _BFR, _MFR, T, E, Pa, GM, RG = {["string.gsub"] = string.gsub, ["math.modf"] = math.modf, ["select"] = select, ["table.concat"] = table.concat, ["error"] = error, ["string.upper"] = string.upper, ["string.sub"] = string.sub, ["debug.sethook"] = debug.sethook, ["debug.traceback"] = debug.traceback, ["debug.getinfo"] = debug.getinfo, ["debug.getupvalue"] = debug.getupvalue, ["collectgarbage"] = collectgarbage, ["os.exit"] = os.exit, ["string.gmatch"] = string.gmatch, ["load"] = load, ["os.time"] = os.time, ["math.deg"] = math.deg, ["math.sqrt"] = math.sqrt, ["string.reverse"] = string.reverse, ["assert"] = assert, ["os.clock"] = os.clock, ["type"] = type, ["math.tan"] = math.tan, ["os.difftime"] = os.difftime, ["math.asin"] = math.asin, ["rawget"] = rawget, ["math.ceil"] = math.ceil, ["string.dump"] = string.dump, ["math.rad"] = math.rad, ["string.len"] = string.len, ["debug.setupvalue"] = debug.setupvalue, ["string.find"] = string.find, ["math.max"] = math.max, ["math.fmod"] = math.fmod, ["math.floor"] = math.floor, ["tonumber"] = tonumber, ["setmetatable"] = setmetatable, ["debug.getlocal"] = debug.getlocal, ["table.remove"] = table.remove, ["pcall"] = pcall, ["math.cos"] = math.cos, ["xpcall"] = xpcall, ["string.match"] = string.match, ["table.insert"] = table.insert, ["rawequal"] = rawequal, ["rawset"] = rawset, ["math.acos"] = math.acos, ["math.abs"] = math.abs, ["getmetatable"] = getmetatable, ["next"] = next, ["table.sort"] = table.sort, ["loadfile"] = loadfile, ["math.atan"] = math.atan, ["string.format"] = string.format, ["tostring"] = tostring, ["dofile"] = dofile, ["string.byte"] = string.byte, ["string.char"] = string.char, ["math.min"] = math.min, ["math.sin"] = math.sin, ["string.lower"] = string.lower, ["math.exp"] = math.exp, ["string.rep"] = string.rep, ["os.date"] = os.date}, {}, type, error, pairs, getmetatable, rawget;
                    local DG = {table = table, string = string, math = math, os = os};
                    local function check()
                        for n, ref in Pa(_BFR) do
                            if ref == nil then
                                E("Tamper Detected! Reason: Critical function removed: ".. n);
                                return
                            end
                            if T(ref) ~= "function" then
                                E("Tamper Detected! Reason: Critical function type changed: ".. n .. " (was function, now ".. T(ref) .. ")");
                                return
                            end
                        end
                        for tname in Pa(_MFR) do
                            local parts = {};
                            for p in tname:gmatch("[^.]+") do
                                parts[#parts + 1] = p
                            end
                            local t = DG[(parts[1])];
                            if t then
                                local mt = GM(t);
                                if mt then
                                    local mf = RG(mt, parts[2]);
                                    if mf then
                                        local expected = _MFR[tname];
                                        if T(mf) ~= expected then
                                            E("Tamper Detected! Reason: Metamethod tampered: ".. tname);
                                            return
                                        end
                                    end
                                end
                            end
                        end
                        local d = debug;
                        if T(d) == "table" then
                            local _DK = {"getinfo", "getlocal", "getupvalue", "traceback", "sethook", "setupvalue"};
                            for _, k in Pa(_DK) do
                                if T(d[k]) ~= "function" then
                                    E("Tamper Detected! Reason: Debug library incomplete");
                                    return
                                end
                            end
                        end
                    end check()
                end
                local YYGSNIJM, otVEpHdtrllt, eGCsiWtBID, yNNxTFpdIN, FZexajrU, likwOuOeA, MyhCPbTRaa, bhxtvCltuCyb, xtghVnCy, xuegBamofm;
                YYGSNIJM = ipairs;
                otVEpHdtrllt = pairs;
                eGCsiWtBID = print;
                yNNxTFpdIN = math.floor;
                FZexajrU = string.byte;
                likwOuOeA = string.char;
                MyhCPbTRaa = string.format;
                bhxtvCltuCyb = string.sub;
                xtghVnCy = table.concat;
                xuegBamofm = table.insert;
                local SyMDHRvxm = {[32] = " ", [37] = "%", [43] = "+", [44] = ",", [45] = "-", [46] = ".", [47] = "/", [48] = "0", [49] = "1", [50] = "2", [51] = "3", [52] = "4", [53] = "5", [54] = "6", [55] = "7", [56] = "8", [57] = "9", [58] = ":", [61] = "=", [65] = "A", [66] = "B", [67] = "C", [68] = "D", [69] = "E", [70] = "F", [71] = "G", [72] = "H", [73] = "I", [74] = "J", [75] = "K", [76] = "L", [77] = "M", [78] = "N", [79] = "O", [80] = "P", [81] = "Q", [82] = "R", [83] = "S", [84] = "T", [85] = "U", [86] = "V", [87] = "W", [88] = "X", [89] = "Y", [90] = "Z", [95] = "_", [97] = "a", [98] = "b", [99] = "c", [100] = "d", [101] = "e", [102] = "f", [103] = "g", [104] = "h", [105] = "i", [106] = "j", [107] = "k", [108] = "l", [109] = "m", [110] = "n", [111] = "o", [112] = "p", [113] = "q", [114] = "r", [115] = "s", [116] = "t", [117] = "u", [118] = "v", [119] = "w", [120] = "x", [121] = "y", [122] = "z"};
                local eydHNekUI = (function (gJipgjqtagCP, LyqPIFfIATTP)
                    local VeqkfAGB = {};
                    for woUCOydB = 1, #gJipgjqtagCP do
                        local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                        if (function (EMlUpRpAMDoU)
                            return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                        end)(EMlUpRpAMDoU) then
                            local WHhGGYvmbWK
                            if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                    elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                    end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                    else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                end
                            end
                            return table.concat(VeqkfAGB)
                        end)((SyMDHRvxm[- 448 + 538] .. SyMDHRvxm[- 639 + 704] .. SyMDHRvxm[- 125 + 191] .. SyMDHRvxm[- 570 + 637] .. SyMDHRvxm[347 - (279)] .. SyMDHRvxm[- 232 + 301] .. SyMDHRvxm[- 572 + 642] .. SyMDHRvxm[228 - (157)] .. SyMDHRvxm[- 550 + 622] .. SyMDHRvxm[- 331 + 404] .. SyMDHRvxm[- 848 + 922] .. SyMDHRvxm[- 111 + 186] .. SyMDHRvxm[- 129 + 205] .. SyMDHRvxm[629 - (552)] .. SyMDHRvxm[- 55 + 133] .. SyMDHRvxm[488 - (409)] .. SyMDHRvxm[- 53 + 133] .. SyMDHRvxm[- 689 + 770] .. SyMDHRvxm[773 - (691)] .. SyMDHRvxm[156 - (73)] .. SyMDHRvxm[142 - (58)] .. SyMDHRvxm[197 - (112)] .. SyMDHRvxm[948 - (862)] .. SyMDHRvxm[862 - (775)] .. SyMDHRvxm[995 - (907)] .. SyMDHRvxm[- 243 + 332] .. SyMDHRvxm[- 274 + 396] .. SyMDHRvxm[- 824 + 921] .. SyMDHRvxm[- 7 + 105] .. SyMDHRvxm[152 - (53)] .. SyMDHRvxm[858 - (758)] .. SyMDHRvxm[875 - (774)] .. SyMDHRvxm[- 168 + 270] .. SyMDHRvxm[- 299 + 402] .. SyMDHRvxm[- 417 + 521] .. SyMDHRvxm[- 721 + 826] .. SyMDHRvxm[- 509 + 615] .. SyMDHRvxm[- 854 + 961] .. SyMDHRvxm[624 - (516)] .. SyMDHRvxm[937 - (828)] .. SyMDHRvxm[162 - (52)] .. SyMDHRvxm[138 - (27)] .. SyMDHRvxm[517 - (405)] .. SyMDHRvxm[268 - (155)] .. SyMDHRvxm[654 - (540)] .. SyMDHRvxm[- 43 + 158] .. SyMDHRvxm[258 - (142)] .. SyMDHRvxm[108 - (- 9)] .. SyMDHRvxm[- 329 + 447] .. SyMDHRvxm[- 370 + 489] .. SyMDHRvxm[- 440 + 560] .. SyMDHRvxm[- 669 + 790] .. SyMDHRvxm[908 - (855)] .. SyMDHRvxm[216 - (162)] .. SyMDHRvxm[244 - (189)] .. SyMDHRvxm[- 612 + 668] .. SyMDHRvxm[- 162 + 219] .. SyMDHRvxm[329 - (281)] .. SyMDHRvxm[- 398 + 447] .. SyMDHRvxm[809 - (759)] .. SyMDHRvxm[746 - (695)] .. SyMDHRvxm[- 358 + 410] .. SyMDHRvxm[907 - (864)] .. SyMDHRvxm[- 733 + 780]), 25);
                        local vgXVvmhn = (function (gJipgjqtagCP, LyqPIFfIATTP)
                            local VeqkfAGB = {};
                            for woUCOydB = 1, #gJipgjqtagCP do
                                local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                if (function (EMlUpRpAMDoU)
                                    return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                end)(EMlUpRpAMDoU) then
                                    local WHhGGYvmbWK
                                    if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                        elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                            elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                            end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                            else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                        end
                                    end
                                    return table.concat(VeqkfAGB)
                                end)((SyMDHRvxm[939 - (869)] .. SyMDHRvxm[957 - (858)] .. SyMDHRvxm[660 - (548)] .. SyMDHRvxm[- 694 + 791] .. SyMDHRvxm[- 643 + 758] .. SyMDHRvxm[679 - (573)] .. SyMDHRvxm[- 395 + 494] .. SyMDHRvxm[178 - (65)] .. SyMDHRvxm[202 - (157)] .. SyMDHRvxm[- 273 + 355] .. SyMDHRvxm[- 400 + 499] .. SyMDHRvxm[- 706 + 819] .. SyMDHRvxm[861 - (747)] .. SyMDHRvxm[877 - (832)] .. SyMDHRvxm[330 - (276)] .. SyMDHRvxm[- 380 + 432] .. SyMDHRvxm[122 - (68)] .. SyMDHRvxm[365 - (317)]), 24);
                                local gWTITyFlHo = {(function (gJipgjqtagCP, LyqPIFfIATTP)
                                    local VeqkfAGB = {};
                                    for woUCOydB = 1, #gJipgjqtagCP do
                                        local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                        if (function (EMlUpRpAMDoU)
                                            return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                        end)(EMlUpRpAMDoU) then
                                            local WHhGGYvmbWK
                                            if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                    elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                    end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                    else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                end
                                            end
                                            return table.concat(VeqkfAGB)
                                        end)((SyMDHRvxm[- 77 + 178] .. SyMDHRvxm[- 644 + 742] .. SyMDHRvxm[- 52 + 157] .. SyMDHRvxm[410 - (305)] .. SyMDHRvxm[- 418 + 526]), 23), (function (gJipgjqtagCP, LyqPIFfIATTP)
                                            local VeqkfAGB = {};
                                            for woUCOydB = 1, #gJipgjqtagCP do
                                                local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                if (function (EMlUpRpAMDoU)
                                                    return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                end)(EMlUpRpAMDoU) then
                                                    local WHhGGYvmbWK
                                                    if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                        elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                            elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                            end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                            else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                        end
                                                    end
                                                    return table.concat(VeqkfAGB)
                                                end)((SyMDHRvxm[- 32 + 147] .. SyMDHRvxm[975 - (872)] .. SyMDHRvxm[706 - (606)] .. SyMDHRvxm[- 841 + 873] .. SyMDHRvxm[133 - (21)] .. SyMDHRvxm[298 - (182)] .. SyMDHRvxm[375 - (271)] .. SyMDHRvxm[184 - (86)] .. SyMDHRvxm[- 605 + 711] .. SyMDHRvxm[607 - (575)] .. SyMDHRvxm[353 - (256)] .. SyMDHRvxm[964 - (851)] .. SyMDHRvxm[682 - (572)] .. SyMDHRvxm[- 45 + 163] .. SyMDHRvxm[204 - (95)] .. SyMDHRvxm[528 - (496)] .. SyMDHRvxm[227 - (126)] .. SyMDHRvxm[445 - (335)] .. SyMDHRvxm[912 - (793)]), 25), (function (gJipgjqtagCP, LyqPIFfIATTP)
                                                    local VeqkfAGB = {};
                                                    for woUCOydB = 1, #gJipgjqtagCP do
                                                        local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                        if (function (EMlUpRpAMDoU)
                                                            return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                        end)(EMlUpRpAMDoU) then
                                                            local WHhGGYvmbWK
                                                            if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                    elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                    end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                    else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                end
                                                            end
                                                            return table.concat(VeqkfAGB)
                                                        end)((SyMDHRvxm[- 788 + 857] .. SyMDHRvxm[- 817 + 915] .. SyMDHRvxm[- 220 + 331] .. SyMDHRvxm[- 509 + 631] .. SyMDHRvxm[752 - (638)] .. SyMDHRvxm[780 - (675)] .. SyMDHRvxm[210 - (112)] .. SyMDHRvxm[- 822 + 934] .. SyMDHRvxm[- 751 + 783] .. SyMDHRvxm[111 - (- 5)] .. SyMDHRvxm[841 - (721)] .. SyMDHRvxm[- 254 + 366] .. SyMDHRvxm[- 663 + 695] .. SyMDHRvxm[809 - (708)] .. SyMDHRvxm[150 - (52)] .. SyMDHRvxm[677 - (566)] .. SyMDHRvxm[- 633 + 731]), 23), };
                                                        if true then
                                                            do
                                                                (function ()
                                                                    eGCsiWtBID((function (gJipgjqtagCP, LyqPIFfIATTP)
                                                                        local VeqkfAGB = {};
                                                                        for woUCOydB = 1, #gJipgjqtagCP do
                                                                            local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                                            if (function (EMlUpRpAMDoU)
                                                                                return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                                            end)(EMlUpRpAMDoU) then
                                                                                local WHhGGYvmbWK
                                                                                if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                                    elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                                        elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                                        end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                                        else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                                    end
                                                                                end
                                                                                return table.concat(VeqkfAGB)
                                                                            end)((SyMDHRvxm[698 - (637)] .. SyMDHRvxm[351 - (290)] .. SyMDHRvxm[560 - (499)] .. SyMDHRvxm[467 - (435)] .. SyMDHRvxm[712 - (642)] .. SyMDHRvxm[538 - (439)] .. SyMDHRvxm[305 - (193)] .. SyMDHRvxm[555 - (458)] .. SyMDHRvxm[723 - (608)] .. SyMDHRvxm[- 335 + 441] .. SyMDHRvxm[846 - (747)] .. SyMDHRvxm[- 123 + 236] .. SyMDHRvxm[240 - (208)] .. SyMDHRvxm[617 - (551)] .. SyMDHRvxm[- 41 + 140] .. SyMDHRvxm[- 376 + 485] .. SyMDHRvxm[533 - (411)] .. SyMDHRvxm[- 886 + 986] .. SyMDHRvxm[- 845 + 960] .. SyMDHRvxm[361 - (248)] .. SyMDHRvxm[656 - (559)] .. SyMDHRvxm[801 - (680)] .. SyMDHRvxm[- 805 + 919] .. SyMDHRvxm[979 - (876)] .. SyMDHRvxm[- 109 + 218] .. SyMDHRvxm[382 - (274)] .. SyMDHRvxm[- 761 + 793] .. SyMDHRvxm[755 - (690)] .. SyMDHRvxm[268 - (166)] .. SyMDHRvxm[- 504 + 625] .. SyMDHRvxm[854 - (748)] .. SyMDHRvxm[631 - (525)] .. SyMDHRvxm[403 - (304)] .. SyMDHRvxm[332 - (224)] .. SyMDHRvxm[669 - (568)] .. SyMDHRvxm[310 - (211)] .. SyMDHRvxm[571 - (539)] .. SyMDHRvxm[- 440 + 501] .. SyMDHRvxm[- 637 + 698] .. SyMDHRvxm[- 45 + 106]), 24))
                                                                        end)()
                                                                    end do
                                                                        (function ()
                                                                            eGCsiWtBID((function (gJipgjqtagCP, LyqPIFfIATTP)
                                                                                local VeqkfAGB = {};
                                                                                for woUCOydB = 1, #gJipgjqtagCP do
                                                                                    local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                                                    if (function (EMlUpRpAMDoU)
                                                                                        return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                                                    end)(EMlUpRpAMDoU) then
                                                                                        local WHhGGYvmbWK
                                                                                        if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                                            elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                                                WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                                                elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                                                end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                                                else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                                            end
                                                                                        end
                                                                                        return table.concat(VeqkfAGB)
                                                                                    end)((SyMDHRvxm[829 - (748)] .. SyMDHRvxm[- 211 + 331] .. SyMDHRvxm[- 287 + 398] .. SyMDHRvxm[- 825 + 925] .. SyMDHRvxm[- 831 + 929] .. SyMDHRvxm[352 - (239)] .. SyMDHRvxm[- 809 + 867] .. SyMDHRvxm[- 481 + 513] .. SyMDHRvxm[- 95 + 206] .. SyMDHRvxm[128 - (30)] .. SyMDHRvxm[834 - (712)] .. SyMDHRvxm[- 789 + 897] .. SyMDHRvxm[544 - (429)] .. SyMDHRvxm[- 882 + 980] .. SyMDHRvxm[228 - (117)] .. SyMDHRvxm[- 266 + 298] .. SyMDHRvxm[- 475 + 574] .. SyMDHRvxm[- 440 + 547] .. SyMDHRvxm[834 - (719)] .. SyMDHRvxm[- 454 + 506] .. SyMDHRvxm[- 721 + 841] .. SyMDHRvxm[972 - (877)] .. SyMDHRvxm[860 - (806)] .. SyMDHRvxm[- 225 + 278] .. SyMDHRvxm[- 468 + 512] .. SyMDHRvxm[- 775 + 807] .. SyMDHRvxm[478 - (357)] .. SyMDHRvxm[12 + 108] .. SyMDHRvxm[- 645 + 757] .. SyMDHRvxm[651 - (553)] .. SyMDHRvxm[604 - (547)] .. SyMDHRvxm[- 917 + 972] .. SyMDHRvxm[388 - (293)] .. SyMDHRvxm[994 - (896)] .. SyMDHRvxm[698 - (591)] .. SyMDHRvxm[450 - (328)] .. SyMDHRvxm[760 - (652)] .. SyMDHRvxm[494 - (397)] .. SyMDHRvxm[- 215 + 313] .. SyMDHRvxm[- 340 + 384] .. SyMDHRvxm[- 214 + 246] .. SyMDHRvxm[- 286 + 408] .. SyMDHRvxm[- 375 + 476] .. SyMDHRvxm[799 - (701)] .. SyMDHRvxm[- 852 + 974] .. SyMDHRvxm[162 - (58)] .. SyMDHRvxm[- 258 + 370] .. SyMDHRvxm[229 - (115)] .. SyMDHRvxm[160 - (54)] .. SyMDHRvxm[132 - (88)] .. SyMDHRvxm[620 - (588)] .. SyMDHRvxm[- 112 + 192] .. SyMDHRvxm[218 - (152)] .. SyMDHRvxm[414 - (324)] .. SyMDHRvxm[- 683 + 762] .. SyMDHRvxm[- 213 + 279] .. SyMDHRvxm[102 - (21)] .. SyMDHRvxm[898 - (803)] .. SyMDHRvxm[- 248 + 320] .. SyMDHRvxm[829 - (763)] .. SyMDHRvxm[785 - (699)]), 23))
                                                                                end)()
                                                                            end
                                                                        end
                                                                        if 30 % 30 == 0 then
                                                                            do
                                                                                (function ()
                                                                                    eGCsiWtBID((function (gJipgjqtagCP, LyqPIFfIATTP)
                                                                                        local VeqkfAGB = {};
                                                                                        for woUCOydB = 1, #gJipgjqtagCP do
                                                                                            local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                                                            if (function (EMlUpRpAMDoU)
                                                                                                return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                                                            end)(EMlUpRpAMDoU) then
                                                                                                local WHhGGYvmbWK
                                                                                                if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                                                    elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                                                        elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                                                        end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                                                        else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                                                    end
                                                                                                end
                                                                                                return table.concat(VeqkfAGB)
                                                                                            end)((""), 1))
                                                                                        end)()
                                                                                    end
                                                                                end
                                                                                for _, sample in YYGSNIJM(gWTITyFlHo) do
                                                                                    local FzmRiydh = (function (data)
                                                                                        local xiFrrnfipR = {};
                                                                                        local BtjhOWlvPpi = #data;
                                                                                        local woUCOydB = 1;
                                                                                        while woUCOydB <= BtjhOWlvPpi do
                                                                                            local iAqCJBKpsb = string.byte(data, woUCOydB) or 0;
                                                                                            local SkAEmbFW = string.byte(data, woUCOydB + 1) or 0;
                                                                                            local iCeDyLzIDAOn = string.byte(data, woUCOydB + 2) or 0;
                                                                                            local AxwYOQGrhZB = iAqCJBKpsb * 65536 + SkAEmbFW * 256 + iCeDyLzIDAOn;
                                                                                            local wqqrpnuqX = math.floor(AxwYOQGrhZB / 262144) % 64;
                                                                                            local wLSMQDCl = math.floor(AxwYOQGrhZB / 4096) % 64;
                                                                                            local KeEAJJUCg = math.floor(AxwYOQGrhZB / 64) % 64;
                                                                                            local YORqmPcv = AxwYOQGrhZB % 64;
                                                                                            do
                                                                                                (function ()
                                                                                                    xiFrrnfipR[#xiFrrnfipR + 1] = string.sub(eydHNekUI, wqqrpnuqX + 1, wqqrpnuqX + 1)
                                                                                                end)()
                                                                                            end do
                                                                                                (function ()
                                                                                                    xiFrrnfipR[#xiFrrnfipR + 1] = string.sub(eydHNekUI, wLSMQDCl + 1, wLSMQDCl + 1)
                                                                                                end)()
                                                                                            end
                                                                                            if woUCOydB + 1 <= BtjhOWlvPpi then
                                                                                                do
                                                                                                    (function ()
                                                                                                        xiFrrnfipR[#xiFrrnfipR + 1] = string.sub(eydHNekUI, KeEAJJUCg + 1, KeEAJJUCg + 1)
                                                                                                    end)()
                                                                                                end
                                                                                                else do
                                                                                                    (function ()
                                                                                                        xiFrrnfipR[#xiFrrnfipR + 1] = (function (gJipgjqtagCP, LyqPIFfIATTP)
                                                                                                            local VeqkfAGB = {};
                                                                                                            for woUCOydB = 1, #gJipgjqtagCP do
                                                                                                                local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                                                                                if (function (EMlUpRpAMDoU)
                                                                                                                    return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                                                                                end)(EMlUpRpAMDoU) then
                                                                                                                    local WHhGGYvmbWK
                                                                                                                    if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                                                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                                                                        elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                                                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                                                                            elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                                                                                WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                                                                            end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                                                                            else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                                                                        end
                                                                                                                    end
                                                                                                                    return table.concat(VeqkfAGB)
                                                                                                                end)((SyMDHRvxm[573 - (512)]), 1)
                                                                                                            end)()
                                                                                                        end
                                                                                                    end
                                                                                                    if woUCOydB + 2 <= BtjhOWlvPpi then
                                                                                                        do
                                                                                                            (function ()
                                                                                                                xiFrrnfipR[#xiFrrnfipR + 1] = string.sub(eydHNekUI, YORqmPcv + 1, YORqmPcv + 1)
                                                                                                            end)()
                                                                                                        end
                                                                                                        else do
                                                                                                            (function ()
                                                                                                                xiFrrnfipR[#xiFrrnfipR + 1] = (function (gJipgjqtagCP, LyqPIFfIATTP)
                                                                                                                    local VeqkfAGB = {};
                                                                                                                    for woUCOydB = 1, #gJipgjqtagCP do
                                                                                                                        local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                                                                                        if (function (EMlUpRpAMDoU)
                                                                                                                            return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                                                                                        end)(EMlUpRpAMDoU) then
                                                                                                                            local WHhGGYvmbWK
                                                                                                                            if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                                                                                WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                                                                                elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                                                                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                                                                                    elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                                                                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                                                                                    end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                                                                                    else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                                                                                end
                                                                                                                            end
                                                                                                                            return table.concat(VeqkfAGB)
                                                                                                                        end)((SyMDHRvxm[718 - (657)]), 1)
                                                                                                                    end)()
                                                                                                                end
                                                                                                            end do
                                                                                                                (function ()
                                                                                                                    woUCOydB = woUCOydB + 3
                                                                                                                end)()
                                                                                                            end
                                                                                                        end
                                                                                                        return table.concat(xiFrrnfipR)
                                                                                                    end)(sample);
                                                                                                    local QuXpVMtNTFlm = (function (payload)
                                                                                                        return string.format((function (gJipgjqtagCP, LyqPIFfIATTP)
                                                                                                            local VeqkfAGB = {};
                                                                                                            for woUCOydB = 1, #gJipgjqtagCP do
                                                                                                                local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                                                                                if (function (EMlUpRpAMDoU)
                                                                                                                    return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                                                                                end)(EMlUpRpAMDoU) then
                                                                                                                    local WHhGGYvmbWK
                                                                                                                    if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                                                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                                                                        elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                                                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                                                                            elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                                                                                WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                                                                            end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                                                                            else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                                                                        end
                                                                                                                    end
                                                                                                                    return table.concat(VeqkfAGB)
                                                                                                                end)((SyMDHRvxm[- 531 + 568] .. SyMDHRvxm[409 - (358)] .. SyMDHRvxm[661 - (612)] .. SyMDHRvxm[- 288 + 405]), 23), (function (text)
                                                                                                                    local KZrabrwJnW = 0x811c9dc5;
                                                                                                                    for woUCOydB = 1, #text do
                                                                                                                        local CNiAnCeaAoaw = string.byte(text, woUCOydB);
                                                                                                                        KZrabrwJnW = KZrabrwJnW ~ CNiAnCeaAoaw;
                                                                                                                        do
                                                                                                                            (function ()
                                                                                                                                KZrabrwJnW = (KZrabrwJnW * 0x01000193) % 0x100000000
                                                                                                                            end)()
                                                                                                                        end
                                                                                                                    end
                                                                                                                    return KZrabrwJnW
                                                                                                                end)(payload .. vgXVvmhn))
                                                                                                            end)(sample);
                                                                                                            do
                                                                                                                (function ()
                                                                                                                    eGCsiWtBID(string.format((function (gJipgjqtagCP, LyqPIFfIATTP)
                                                                                                                        local VeqkfAGB = {};
                                                                                                                        for woUCOydB = 1, #gJipgjqtagCP do
                                                                                                                            local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                                                                                            if (function (EMlUpRpAMDoU)
                                                                                                                                return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                                                                                            end)(EMlUpRpAMDoU) then
                                                                                                                                local WHhGGYvmbWK
                                                                                                                                if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                                                                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                                                                                    elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                                                                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                                                                                        elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                                                                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                                                                                        end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                                                                                        else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                                                                                    end
                                                                                                                                end
                                                                                                                                return table.concat(VeqkfAGB)
                                                                                                                            end)((SyMDHRvxm[- 521 + 620] .. SyMDHRvxm[- 455 + 559] .. SyMDHRvxm[765 - (659)] .. SyMDHRvxm[- 593 + 704] .. SyMDHRvxm[526 - (416)] .. SyMDHRvxm[761 - (729)] .. SyMDHRvxm[- 123 + 155] .. SyMDHRvxm[- 82 + 114] .. SyMDHRvxm[279 - (247)] .. SyMDHRvxm[362 - (304)] .. SyMDHRvxm[178 - (146)] .. SyMDHRvxm[- 357 + 394] .. SyMDHRvxm[- 572 + 679]), 20), sample))
                                                                                                                        end)()
                                                                                                                    end do
                                                                                                                        (function ()
                                                                                                                            eGCsiWtBID(string.format((function (gJipgjqtagCP, LyqPIFfIATTP)
                                                                                                                                local VeqkfAGB = {};
                                                                                                                                for woUCOydB = 1, #gJipgjqtagCP do
                                                                                                                                    local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                                                                                                    if (function (EMlUpRpAMDoU)
                                                                                                                                        return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                                                                                                    end)(EMlUpRpAMDoU) then
                                                                                                                                        local WHhGGYvmbWK
                                                                                                                                        if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                                                                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                                                                                            elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                                                                                                WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                                                                                                elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                                                                                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                                                                                                end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                                                                                                else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                                                                                            end
                                                                                                                                        end
                                                                                                                                        return table.concat(VeqkfAGB)
                                                                                                                                    end)((SyMDHRvxm[- 143 + 240] .. SyMDHRvxm[- 403 + 525] .. SyMDHRvxm[- 216 + 330] .. SyMDHRvxm[- 326 + 426] .. SyMDHRvxm[- 613 + 662] .. SyMDHRvxm[- 723 + 780] .. SyMDHRvxm[798 - (766)] .. SyMDHRvxm[- 267 + 299] .. SyMDHRvxm[- 144 + 176] .. SyMDHRvxm[108 - (50)] .. SyMDHRvxm[527 - (495)] .. SyMDHRvxm[- 248 + 285] .. SyMDHRvxm[- 467 + 581]), 25), FzmRiydh))
                                                                                                                                end)()
                                                                                                                            end do
                                                                                                                                (function ()
                                                                                                                                    eGCsiWtBID(string.format((function (gJipgjqtagCP, LyqPIFfIATTP)
                                                                                                                                        local VeqkfAGB = {};
                                                                                                                                        for woUCOydB = 1, #gJipgjqtagCP do
                                                                                                                                            local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                                                                                                            if (function (EMlUpRpAMDoU)
                                                                                                                                                return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                                                                                                            end)(EMlUpRpAMDoU) then
                                                                                                                                                local WHhGGYvmbWK
                                                                                                                                                if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                                                                                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                                                                                                    elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                                                                                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                                                                                                        elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                                                                                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                                                                                                        end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                                                                                                        else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                                                                                                    end
                                                                                                                                                end
                                                                                                                                                return table.concat(VeqkfAGB)
                                                                                                                                            end)((SyMDHRvxm[- 613 + 734] .. SyMDHRvxm[- 177 + 277] .. SyMDHRvxm[- 867 + 964] .. SyMDHRvxm[- 300 + 421] .. SyMDHRvxm[453 - (350)] .. SyMDHRvxm[- 2 + 113] .. SyMDHRvxm[835 - (722)] .. SyMDHRvxm[- 127 + 232] .. SyMDHRvxm[784 - (752)] .. SyMDHRvxm[240 - (182)] .. SyMDHRvxm[259 - (227)] .. SyMDHRvxm[668 - (631)] .. SyMDHRvxm[- 208 + 319]), 22), QuXpVMtNTFlm))
                                                                                                                                        end)()
                                                                                                                                    end do
                                                                                                                                        (function ()
                                                                                                                                            eGCsiWtBID((function (gJipgjqtagCP, LyqPIFfIATTP)
                                                                                                                                                local VeqkfAGB = {};
                                                                                                                                                for woUCOydB = 1, #gJipgjqtagCP do
                                                                                                                                                    local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                                                                                                                    if (function (EMlUpRpAMDoU)
                                                                                                                                                        return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                                                                                                                    end)(EMlUpRpAMDoU) then
                                                                                                                                                        local WHhGGYvmbWK
                                                                                                                                                        if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                                                                                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                                                                                                            elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                                                                                                                WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                                                                                                                elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                                                                                                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                                                                                                                end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                                                                                                                else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                                                                                                            end
                                                                                                                                                        end
                                                                                                                                                        return table.concat(VeqkfAGB)
                                                                                                                                                    end)((""), 1))
                                                                                                                                                end)()
                                                                                                                                            end
                                                                                                                                        end
                                                                                                                                        if (not (2 >= 58)) == (2 < 58) then
                                                                                                                                            do
                                                                                                                                                (function ()
                                                                                                                                                    eGCsiWtBID((function (gJipgjqtagCP, LyqPIFfIATTP)
                                                                                                                                                        local VeqkfAGB = {};
                                                                                                                                                        for woUCOydB = 1, #gJipgjqtagCP do
                                                                                                                                                            local EMlUpRpAMDoU = gJipgjqtagCP:byte(woUCOydB);
                                                                                                                                                            if (function (EMlUpRpAMDoU)
                                                                                                                                                                return (EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57) or (EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90) or (EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122)
                                                                                                                                                            end)(EMlUpRpAMDoU) then
                                                                                                                                                                local WHhGGYvmbWK
                                                                                                                                                                if EMlUpRpAMDoU >= 48 and EMlUpRpAMDoU <= 57 then
                                                                                                                                                                    WHhGGYvmbWK = ((EMlUpRpAMDoU - 48 - LyqPIFfIATTP + 10) % 10) + 48
                                                                                                                                                                    elseif EMlUpRpAMDoU >= 65 and EMlUpRpAMDoU <= 90 then
                                                                                                                                                                        WHhGGYvmbWK = ((EMlUpRpAMDoU - 65 - LyqPIFfIATTP + 26) % 26) + 65
                                                                                                                                                                        elseif EMlUpRpAMDoU >= 97 and EMlUpRpAMDoU <= 122 then
                                                                                                                                                                            WHhGGYvmbWK = ((EMlUpRpAMDoU - 97 - LyqPIFfIATTP + 26) % 26) + 97
                                                                                                                                                                        end table.insert(VeqkfAGB, string.char(WHhGGYvmbWK))
                                                                                                                                                                        else table.insert(VeqkfAGB, string.char(EMlUpRpAMDoU))
                                                                                                                                                                    end
                                                                                                                                                                end
                                                                                                                                                                return table.concat(VeqkfAGB)
                                                                                                                                                            end)((SyMDHRvxm[671 - (574)] .. SyMDHRvxm[- 852 + 960] .. SyMDHRvxm[- 35 + 142] .. SyMDHRvxm[- 435 + 533] .. SyMDHRvxm[- 242 + 288]), 23))
                                                                                                                                                        end)()
                                                                                                                                                    end
                                                                                                                                                    elseif false then
                                                                                                                                                    end
                                                                                                                                                end break
                                                                                                                                            end
                                                                                                                                        end
                                                                                                                                        local mhuyca = 25;
                                                                                                                                        local function accqhm(rjwqit)
                                                                                                                                            local _ = 9
                                                                                                                                        end
                                                                                                                                        local hprzzh = 22;
                                                                                                                                        local ogojab = 35;
                                                                                                                                        local function cxutzt(tzbqpn)
                                                                                                                                            local _ = 74
                                                                                                                                        end
                                                                                                                                        local ujblbu = 3;
                                                                                                                                        local function inpnrd(blwtoe)
                                                                                                                                            local _ = 24
                                                                                                                                        end
                                                                                                                                        if false then
                                                                                                                                            local _ = 26
                                                                                                                                        end
                                                                                                                                        if false then
                                                                                                                                            local _ = 44
                                                                                                                                        end
                                                                                                                                        local function egtimj(miqnvz)
                                                                                                                                            local _ = 93
                                                                                                                                        end
                                                                                                                                        local function uwmpim(aipssf)
                                                                                                                                            local _ = 91
                                                                                                                                        end
                                                                                                                                        local djgrqj = 41;
                                                                                                                                        local function xmwisn(nwgnhb)
                                                                                                                                            local _ = 37
                                                                                                                                        end
                                                                                                                                    end)()
