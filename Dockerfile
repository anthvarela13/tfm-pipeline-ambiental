FROM python:3.10-slim
RUN pip install --no-cache-dir \
    jupyterlab \
    scikit-learn==1.5.2 matplotlib==3.9.2 seaborn==0.13.2 \
    pandas==2.2.3 numpy==2.1.2 pandas matplotlib
WORKDIR /work
EXPOSE 8888
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--allow-root"]