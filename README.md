tạo 1 chương trình dùng playwright, xóa hết dấu hiệu của bot tự động, thêm các dấu hiệu giống người thật để:
1, mở url: @https://my.22.cn/ 
2, nhập tên người dùng "15212172775" và password "291631.." vào :  <div class="login-box">
                                                <input type="text" class="input_registera" maxlength="50" id="input_register" placeholder="ID/邮箱/手机号码">
                                                <input type="password" class="input_registera" value="" maxlength="50" id="input_registera" placeholder="账号登录密码">
                                                <div class="yzm-nouse" style="display:none;">
                                                    <input type="text" class="input_registerb" maxlength="50" id="input_registerb" placeholder="验证码">
                                                    <img tabindex="-1" id="imgid" src="/tools/vcode.aspx?codewidth=100&amp;codeheight=25&amp;rand=Math.random()" onclick="d=new Date(); this.src='/tools/vcode.aspx?codewidth=100&amp;codeheight=25&amp;rand='+ d.getMilliseconds();" style="cursor: pointer;" align="AbsMiddle" class="yzm_img">
                                                    <span class="i_signv"></span><a href="#" tabindex="-1" onclick="d=new Date();document.getElementById('imgid').src='/tools/vcode.aspx?codewidth=100&amp;codeheight=25&amp;rand='+d.getMilliseconds();return false;" title="看不清换一张" class="hui">换一张</a>
                                                    <input type="hidden" id="url" name="url" value="https://www.22.cn/">
                                                    <input type="hidden" id="service" name="service" value="ucs">
                                                    <input type="hidden" id="nonce" name="nonce" value="">
                                                </div>
                                                  <div id="captcha-element" style="width:305px"></div>
                                                <input class="inner_rgist" value="登录" type="button" id="denglu_button">
                                                <div class="remenberI">
                                                    <label class="left">
                                                        <input type="checkbox" class="rememberme" id="rememberme" checked="checked">记住账号</label>
                                                    <span class=" right">
                                                        <a href="/findpassword.html" target="_blank" class="blue" title="忘记密码">忘记密码</a>
                                                    </span>
                                                </div>
                                                <div class="remenberI">
                                                    <label class="left">
                                                        <input type="checkbox" class="rememberme" id="cbx_agree" checked="checked" style="margin-right: 7px;">阅读并同意
                                                    </label>
                                                    <span class=" right">
                                                        <a class="blue" title="爱名网服务协议" href="https://www.22.cn/registrar_agreement.html" target="_blank">《爱名网服务协议》</a>
                                                    </span>
                                                </div>
                                            </div>
3. ấn nút login 
4, check  trạng thái login, nếu có <a href="https://i.22.cn"> thì đã login thành công
5. chuyển hướng đến : https://am.22.cn/ykj/
6, tại thanh thả xuống, chọn 爱名网 : <select class="sm-select" name="registrar" id="registrar">
                <option value="0">全部注册商</option>
                <option value="1">爱名网</option>
                <option value="2">其它注册商</option>
                <option value="3">溢价域名</option>
                
            </select>
7, điền minprice=0, maxprice=100 ở : <li class="showbox-t  showbox-none"><em>价格：</em>
            <input type="text" name="txtMinPrice" id="txtMinPrice" value="0" maxlength="11" class="mo-input sm-input40"><span class="input-line">-</span><input type="text" name="txtMaxPrice" id="txtMaxPrice" value="" maxlength="11" class="mo-input sm-input40">
        </li>
8, ấn nút 搜索: <a class="bnt-green width50" href="javascript:setcookie()" id="btn_search">搜索</a>
9. chọn số lượng hiển thị mỗi page : <a name="a_change_pagecount" data="200">200</a>
10. tại bảng kết quả, phân tích lấy 名称 và  当前价格 tương ứng, lưu vào domain.txt , định dạng 名称,当前价格 . mỗi hàng 1 名称

<table border="0" cellspacing="0" cellpadding="0" class="paimai-tb zhuanti-tb">
                            <thead>
                                <tr>
                                    <th></th>
                                    <th>
                                        <font>名称</font>
                                    </th>
                                    <th class="none">简介<span style="font-size:12px;color:gray;">（数据仅供参考，价值请自行判断）</span>
                                    </th>
                                    <th class="none">注册商
                                    </th>
                                    <th id="price" class="td_click" order="">
                                        <font class="orangea">当前价格</font><span class="sortable"></span>
                                    </th>
                                    <th id="enddate" class="td_click none td_clickesa" order="a">
                                        <font class="orangea">剩余时间</font><span class="sortable"></span>
                                    </th>
                                    <th id="registerdate" class="td_click none" order="">
                                        <font class="orangea">注册时间</font><span class="sortable"></span>
                                    </th>
                                    <th id="rexpiredate" class="td_click none" order="">
                                        <font class="orangea">距到期</font><span class="sortable"></span>
                                    </th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody id="buynow_list"><tr><td><input name="chkDomain" type="checkbox" value="31161471" data-url="/ykj/chujia_31161471.html" data-domain="bosn0769.com" data-price="￥88" style="margin-right:3px" data-isdaiguan="0" data-istg="0" onchange="ChangeCheckDomain()"></td> <td style="text-indent:0px"><a class="blue a-price-title" href="//am.22.cn/ykj/chujia_31161471.html" target="_blank">bosn0769.com</a><div class="small-list-text-2"></div></td><td class="none"><div class="list-tit" title=""></div></td> <td class="none">爱名网</td><td>￥88</td><td class="none">2时43分</td><td class="none">2021-08-22</td><td class="none">1天</td><td><a class="bnt" target="_blank" href="//am.22.cn/ykj/chujia_31161471.html">购买</a><a class="bnt ml5 small-none" onclick="concern(31161471,2)">关注</a></td></tr><tr><td><input name="chkDomain" type="checkbox" value="31433482" data-url="/ykj/chujia_31433482.html" data-domain="lqsd.cn" data-price="￥16" style="margin-right:3px" data-isdaiguan="0" data-istg="0" onchange="ChangeCheckDomain()"></td> <td style="text-indent:0px"><a class="blue a-price-title" href="//am.22.cn/ykj/chujia_31433482.html" target="_blank">lqsd.cn</a><div class="small-list-text-2"></div></td><td class="none"><div class="list-tit" title=""></div></td> <td class="none">爱名网</td><td>￥16</td><td class="none">4时28分</td><td class="none">2025-03-28</td><td class="none">219天</td><td><a class="bnt" target="_blank" href="//am.22.cn/ykj/chujia_31433482.html">购买</a><a class="bnt ml5 small-none" onclick="concern(31433482,2)">关注</a></td></tr>
