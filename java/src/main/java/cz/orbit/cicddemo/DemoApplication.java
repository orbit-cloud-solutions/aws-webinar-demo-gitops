package cz.orbit.cicddemo;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.info.BuildProperties;
import org.springframework.http.HttpHeaders;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class DemoApplication {

    Logger logger = LoggerFactory.getLogger(DemoApplication.class);

    @Autowired
    private BuildProperties buildProperties;


    @RequestMapping("/")
    public String hello(@RequestHeader HttpHeaders headers){
        
        logger.info("Logging test: " + headers.toString() );

        return "CICD Demo: version =  "+buildProperties.getVersion();
    }

    public static void main(final String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }

}
