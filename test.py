import logfix
logfix.init(api_key="API KEY", app_version="VERSION")

# TEST
logfix.log("히히 안녕하세요. 이건 로그랍니다!")
logfix.error("심각한 오류!")
logfix.fatal("CRITICAL ERROR!!")