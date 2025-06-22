FROM stephengpope/no-code-architects-toolkit@sha256:2c3d7de1c692e88197525a49513574a23624a723318b3e80961a335408754f32
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends fontconfig fonts-noto-cjk && \
    rm -rf /var/lib/apt/lists/* && fc-cache -f -v
ENV LANG=ja_JP.UTF-8 LANGUAGE=ja_JP:ja LC_ALL=ja_JP.UTF-8
