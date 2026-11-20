-- 运行期语言入口：只选择语言，实际文字放对应文件。先于 actions/recipe 加载。
local locale_code = LOC.GetLocaleCode()
if locale_code == "zh" or locale_code == "zht" or locale_code == "zhr" then
    modimport("main/string_zh")
else
    modimport("main/string_en")
end
